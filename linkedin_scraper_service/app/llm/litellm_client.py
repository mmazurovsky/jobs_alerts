import json
import logging
import os
from typing import List, Optional, Tuple
import asyncio
from shared.data import ShortJobListing, JobType, RemoteType, FullJobListing
from litellm import acompletion
from langdetect import detect
from googletrans import Translator
from pydantic import Field
_translator = Translator()



async def ensure_english(text: str) -> str:
    """Detect language and translate to English if needed (async)."""
    if not text or not detect or not _translator:
        return text
    try:
        lang = detect(text)
        if lang != 'en':
            translated = await _translator.translate(text, src=lang, dest='en')
            return translated.text
        return text
    except Exception:
        return text

class LiteLLMClient:
    """Client for LLM-based job filtering using DeepSeek via LiteLLM."""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.model = "deepseek/deepseek-chat"
        self.logger = logging.getLogger(__name__)
        # Conservative token limits to ensure we don't exceed model limits
        # DeepSeek-chat has 64k context but we'll be conservative
        self.max_input_tokens = 16000  # Leave room for response tokens
        self.estimated_tokens_per_char = 0.25  # Conservative estimate for English text
        self.job_description_max_length = 2000  # Consistent truncation limit
        
        
        if not self.api_key:
            self.logger.warning("DEEPSEEK_API_KEY not found in environment variables")
    
    async def enrich_jobs(
        self,
        jobs: List[ShortJobListing],
        keywords: str,
        job_types: Optional[List[JobType]] = None,
        remote_types: Optional[List[RemoteType]] = None,
        location: Optional[str] = None,
        filter_text: Optional[str] = None
    ) -> List[FullJobListing]:
        """
        Filter and score jobs using LLM.
        Ensures all job descriptions are in English before evaluation.
        
        Args:
            jobs: List of job listings to evaluate
            keywords: Search keywords/job title (single string)
            job_types: List of JobType objects or None
            remote_types: List of RemoteType objects or None
            location: Location string or None
            filter_text: Additional freeform filter text or None
        
        Returns:
            List of FullJobListing objects with techstack and compatibility scores
        """
        if not jobs:
            return []
            
        if not acompletion or not self.api_key:
            self.logger.warning("LiteLLM not available or API key missing, returning all jobs unfiltered")
            return self._create_fallback_full_jobs(jobs)
        
        try:
            # Pre-translate all job descriptions and titles to English (async)
            jobs_english = []
            for job in jobs:
                title_en = await ensure_english(job.title)
                desc_en = await ensure_english(job.description)
                jobs_english.append(
                    ShortJobListing(
                        title=title_en,
                        company=job.company,
                        location=job.location,
                        link=job.link,
                        created_ago=job.created_ago,
                        description=desc_en
                    )
                )
            
            # Convert parameters to string lists for processing
            keywords_list = [keywords] if keywords else []
            job_types_list = [jt.label for jt in job_types] if job_types else []
            remote_types_list = [rt.label for rt in remote_types] if remote_types else []
            
            # Split jobs into batches based on content length
            all_results = []
            job_batches = self._split_jobs_by_content_length(jobs_english, keywords_list, job_types_list, remote_types_list, location, filter_text)
            
            for batch_idx, (batch_jobs, batch_start_offset) in enumerate(job_batches):
                self.logger.info(f"Processing batch {batch_idx + 1}/{len(job_batches)} with {len(batch_jobs)} jobs (offset: {batch_start_offset})")
                
                batch_results = await self._process_job_batch(
                    batch_jobs, keywords_list, job_types_list, remote_types_list, 
                    location, filter_text, batch_start_offset
                )
                all_results.extend(batch_results)
                
                # Small delay between requests to be respectful
                if batch_idx < len(job_batches) - 1:
                    await asyncio.sleep(0.5)
            
            # Filter out jobs with low compatibility_score 
            all_results.sort(key=lambda x: x.compatibility_score, reverse=True)
            return all_results
            
        except Exception as e:
            self.logger.error(f"LLM filtering failed: {e}")
            return self._create_fallback_full_jobs(jobs)
    
    def _format_job_for_prompt(self, job: ShortJobListing, job_index: int) -> str:
        """Format a single job for inclusion in the LLM prompt."""
        description = job.description[:self.job_description_max_length] if job.description else "No description available"
        if len(job.description or "") > self.job_description_max_length:
            description += "..."
        
        return f"""
Job ID: {job_index}
Title: {job.title}
Company: {job.company}
Location: {job.location}
Posted: {job.created_ago}
Description: {description}
---"""
    
    def _split_jobs_by_content_length(
        self,
        jobs: List[ShortJobListing],
        keywords: List[str],
        job_types: List[str],
        remote_types: List[str],
        location: Optional[str],
        filter_text: Optional[str]
    ) -> List[Tuple[List[ShortJobListing], int]]:
        """
        Split jobs into batches based on content length to stay within token limits.
        Returns list of (batch_jobs, batch_start_offset) tuples.
        """
        # Estimate base prompt size (criteria + instructions)
        base_prompt = self._build_base_prompt(keywords, job_types, remote_types, location, filter_text)
        base_tokens = len(base_prompt) * self.estimated_tokens_per_char
        
        # Reserve tokens for response (estimated ~100 tokens per job for response)
        available_tokens = self.max_input_tokens - base_tokens - (15 * 100)  # Reserve for max 15 jobs response
        
        batches = []
        current_batch = []
        current_batch_tokens = 0
        batch_start_offset = 0
        
        for i, job in enumerate(jobs):
            # Estimate tokens for this job using the consistent formatting method
            job_content = self._format_job_for_prompt(job, i)
            job_tokens = len(job_content) * self.estimated_tokens_per_char
            
            # If adding this job would exceed token limit, start new batch
            if current_batch and (current_batch_tokens + job_tokens > available_tokens):
                batches.append((current_batch.copy(), batch_start_offset))
                current_batch = [job]
                current_batch_tokens = job_tokens
                batch_start_offset = i
            else:
                current_batch.append(job)
                current_batch_tokens += job_tokens
                if not batches and not current_batch[:-1]:  # First job in first batch
                    batch_start_offset = i
        
        # Add the last batch if it has jobs
        if current_batch:
            batches.append((current_batch, batch_start_offset))
        
        self.logger.info(f"Split {len(jobs)} jobs into {len(batches)} batches based on content length")
        return batches

    async def _process_job_batch(
        self,
        jobs: List[ShortJobListing],
        keywords: List[str],
        job_types: List[str],
        remote_types: List[str],
        location: Optional[str],
        filter_text: Optional[str],
        batch_offset: int
    ) -> List[FullJobListing]:
        """Process a batch of jobs through the LLM."""
        
        prompt = self._build_prompt(jobs, keywords, job_types, remote_types, location, filter_text)
        
        response = await acompletion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.api_key,
            temperature=0.1,
            max_tokens=4000,
            timeout=30
        )
        
        content = response.choices[0].message.content
        return self._parse_llm_response(content, jobs, batch_offset)
    
    def _build_base_prompt(
        self,
        keywords: List[str],
        job_types: List[str],
        remote_types: List[str],
        location: Optional[str],
        filter_text: Optional[str]
    ) -> str:
        """Build the base prompt without job listings for token estimation."""
        # Build search criteria section
        criteria_parts = []
        if keywords:
            criteria_parts.append(f"Position Title/Keywords: {', '.join(keywords)}")
        if job_types:
            criteria_parts.append(f"Job Types: {', '.join(job_types)}")
        if remote_types:
            criteria_parts.append(f"Remote Work Types: {', '.join(remote_types)}")
        if location:
            criteria_parts.append(f"Location: {location}")
        if filter_text:
            criteria_parts.append(f"Additional Requirements: {filter_text}")
        
        search_criteria = "\n".join(criteria_parts) if criteria_parts else "No specific criteria provided"
        
        return f"""You are a senior technical recruiter specializing in job matching. Evaluate jobs against search criteria with focus on accuracy and relevance.

SEARCH CRITERIA:
{search_criteria}

EVALUATION PRIORITY (in order of importance):
1. TITLE & KEYWORDS MATCH: Job title similarity to position keywords
2. DESCRIPTION KEYWORDS: How well job description matches search keywords  
3. REMOTE WORK TYPE: Match between job's remote policy and required remote type
4. JOB TYPE: Match between job type (full-time, contract, etc.) and requirements
5. ADDITIONAL REQUIREMENTS: Alignment with freeform filter requirements

SCORING GUIDELINES:
- 90-100: Perfect match (title + keywords + all requirements met)
- 70-89: Strong match (title matches, most requirements met)
- 50-69: Good match (partial title match or strong description match)
- 30-49: Weak match (some keywords match but poor overall fit)
- 0-29: Poor/no match (no significant alignment)

Note: Job titles and descriptions may be in any language, but your response must be in English.

JOBS TO EVALUATE:"""

    def _build_prompt(
        self,
        jobs: List[ShortJobListing],
        keywords: List[str],
        job_types: List[str],
        remote_types: List[str],
        location: Optional[str],
        filter_text: Optional[str]
    ) -> str:
        """Build the complete prompt for LLM evaluation."""
        
        base_prompt = self._build_base_prompt(keywords, job_types, remote_types, location, filter_text)
        
        # Build jobs section using consistent formatting
        jobs_text = "".join(self._format_job_for_prompt(job, i) for i, job in enumerate(jobs))
        
        return f"""{base_prompt}
{jobs_text}

Return ONLY a valid JSON array with this exact structure (no markdown, no extra text):
[
  {{
    "job_id": "0",
    "compatibility_score": 85,
    "techstack": ["Python", "React", "AWS", "Docker"],
    "filter_reason": null
  }},
  {{
    "job_id": "1", 
    "compatibility_score": 0,
    "techstack": ["Java", "Spring Boot", "Kubernetes"],
    "filter_reason": "Requires German language"
  }}
]

REQUIREMENTS:
- job_id: string index (0, 1, 2, etc.) matching job order above
- compatibility_score: integer 0-100 based on evaluation criteria
- techstack: array of technology/skill strings extracted from job description
- filter_reason: null if job is not filtered out, otherwise a short explanation (e.g., 'Requires German language', 'On-site only', etc.)
- If a job is filtered out (compatibility_score 0), filter_reason MUST be provided and explain why.
- Only assign a high compatibility_score if ALL requirements and negative constraints in the filter text are satisfied.
- If a job description contains any requirement that is explicitly forbidden in the filter text (e.g., 'should not have requirement to know German language'), assign a compatibility_score of 0 and explain in filter_reason what requirement was violated.
- Do NOT ignore negative requirements, even if the job matches other criteria.
- NO markdown formatting in response
- NO additional text or explanations"""
    
    def _clean_json_response(self, content: str) -> str:
        """Clean LLM response to extract valid JSON."""
        content = content.strip()
        
        # Remove common markdown patterns
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        # Remove any text before first '[' and after last ']'
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx + 1]
        
        return content.strip()
    
    def _parse_llm_response(self, content: str, original_jobs: List[ShortJobListing], batch_offset: int) -> List[FullJobListing]:
        """Parse LLM response and return FullJobListing objects."""
        try:
            cleaned_content = self._clean_json_response(content)
            results = json.loads(cleaned_content)
            
            # Create a mapping of job indices to results
            results_by_id = {}
            for result in results:
                if not isinstance(result, dict):
                    self.logger.warning(f"Skipping invalid result (not a dict): {result}")
                    continue
                    
                required_keys = ['job_id', 'compatibility_score', 'techstack', 'filter_reason']
                if not all(key in result for key in required_keys):
                    self.logger.warning(f"Skipping result missing required keys: {result}")
                    continue
                
                try:
                    # Parse and validate the result
                    job_id = int(result['job_id'])
                    score = max(0, min(100, int(result['compatibility_score'])))
                    
                    # Ensure techstack is list of strings
                    techstack = result['techstack']
                    if not isinstance(techstack, list):
                        techstack = []
                    techstack = [str(item).strip() for item in techstack if str(item).strip()]
                    
                    filter_reason = result.get('filter_reason')
                    if filter_reason is not None and isinstance(filter_reason, str) and not filter_reason.strip():
                        filter_reason = None
                    
                    results_by_id[job_id] = {
                        'compatibility_score': score,
                        'techstack': techstack,
                        'filter_reason': filter_reason
                    }
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Skipping result with invalid data types: {result}, error: {e}")
                    continue
            
            # Create FullJobListing objects
            full_jobs = []
            for i, job in enumerate(original_jobs):
                llm_result = results_by_id.get(i, {'compatibility_score': 0, 'techstack': [], 'filter_reason': None})
                
                full_job = FullJobListing(
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    link=job.link,
                    created_ago=job.created_ago,
                    techstack=llm_result['techstack'],
                    compatibility_score=llm_result['compatibility_score'],
                    filter_reason=llm_result['filter_reason']
                )
                full_jobs.append(full_job)
            
            return full_jobs
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            self.logger.error(f"Response content: {content[:1000]}...")  # Log first 1000 chars only
            return self._create_fallback_full_jobs(original_jobs)
    
    def _create_fallback_full_jobs(self, jobs: List[ShortJobListing]) -> List[FullJobListing]:
        """Create fallback FullJobListing objects when LLM is unavailable."""
        return [
            FullJobListing(
                title=job.title,
                company=job.company,
                location=job.location,
                link=job.link,
                created_ago=job.created_ago,
                techstack=[],
                compatibility_score=None 
            )
            for job in jobs
        ] 