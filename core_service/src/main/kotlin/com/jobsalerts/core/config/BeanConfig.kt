package com.jobsalerts.core.config

import org.springframework.context.annotation.Configuration

@Configuration
class BeanConfig {
    // Spring Events will be handled automatically by ApplicationEventPublisher
    // No need for manual StreamManager bean
} 