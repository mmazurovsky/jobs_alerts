import asyncio
import logging
from typing import List, Callable, Any, Optional


async def execute_parallel_with_semaphore(
    items: List[Any], 
    async_func: Callable, 
    max_concurrent: int = 3,
    operation_name: str = "operation",
    logger: Optional[logging.Logger] = None
) -> List[Any]:
    """
    Execute async operations in parallel with semaphore-based concurrency control.
    
    Args:
        items: List of items to process
        async_func: Async function that takes (item, index) and returns result
        max_concurrent: Maximum number of concurrent operations
        operation_name: Name for logging purposes
        logger: Logger instance to use, defaults to module logger
        
    Returns:
        List of results in the same order as input items
    """
    if not items:
        return []
    
    # Use provided logger or create a default one
    if logger is None:
        logger = logging.getLogger(__name__)
        
    logger.info(f"Starting parallel {operation_name}: {len(items)} items with max {max_concurrent} concurrent tasks")
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def semaphore_wrapper(item, index: int):
        async with semaphore:
            try:
                return await async_func(item, index)
            except Exception as e:
                logger.error(f"{operation_name} task {index}: Error processing item: {e}")
                return None
    
    # Create tasks for all items
    tasks = [
        semaphore_wrapper(item, i) 
        for i, item in enumerate(items)
    ]
    
    # Execute all tasks with controlled concurrency
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and count successes/failures
        successful_results = []
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"{operation_name} task {i+1} failed with exception: {result}")
                failed_count += 1
                successful_results.append(None)  # Maintain order
            elif result is not None:
                successful_results.append(result)
            else:
                failed_count += 1
                successful_results.append(None)  # Maintain order
        
        success_count = len([r for r in successful_results if r is not None])
        logger.info(f"Parallel {operation_name} completed: {success_count} successful, {failed_count} failed out of {len(items)} total")
        return successful_results
        
    except Exception as e:
        logger.error(f"Error in parallel {operation_name} execution: {e}", exc_info=True)
        return [None] * len(items)  # Return list of Nones maintaining order 