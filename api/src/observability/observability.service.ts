import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as Sentry from '@sentry/node';
import { nodeProfilingIntegration } from '@sentry/profiling-node';

@Injectable()
export class ObservabilityService implements OnModuleInit {
  constructor(private configService: ConfigService) {}

  onModuleInit() {
    this.initSentry();
    this.initOpenTelemetry();
  }

  private initSentry() {
    const dsn = this.configService.get<string>('SENTRY_DSN');

    if (dsn) {
      Sentry.init({
        dsn,
        environment: this.configService.get<string>('NODE_ENV') || 'development',
        integrations: [
          // Add profiling integration
          nodeProfilingIntegration(),
          // Add NestJS integration if available
          new Sentry.Integrations.Http({ tracing: true }),
        ],
        // Performance Monitoring
        tracesSampleRate: this.configService.get<number>('SENTRY_TRACES_SAMPLE_RATE') || 1.0,
        // Release Health
        enableTracing: true,
        // Set profiling sample rate
        profilesSampleRate: 1.0,
      });

      console.log('✅ Sentry initialized');
    } else {
      console.log('⚠️  Sentry DSN not configured, skipping Sentry initialization');
    }
  }

  private initOpenTelemetry() {
    // OpenTelemetry configuration will be added here
    // This is a placeholder for the full OTel setup
    console.log('✅ OpenTelemetry initialized (placeholder)');

    // In production, you would:
    // 1. Configure OTel SDK
    // 2. Set up resource detectors
    // 3. Configure exporters (OTLP to collector)
    // 4. Set up auto-instrumentation
    // 5. Configure sampling
  }

  // Helper methods for custom metrics and tracing
  traceMethod(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const spanName = `${target.constructor.name}.${propertyKey}`;

      // In a full implementation, you would create spans here
      console.log(`🔍 Tracing: ${spanName}`);

      try {
        const result = await originalMethod.apply(this, args);
        console.log(`✅ Trace completed: ${spanName}`);
        return result;
      } catch (error) {
        console.error(`❌ Trace failed: ${spanName}`, error);
        // In full implementation, record exception on span
        throw error;
      }
    };

    return descriptor;
  }

  incrementCounter(metricName: string, value = 1, tags: Record<string, string> = {}) {
    // Placeholder for metrics
    console.log(`📊 Counter ${metricName}: +${value}`, tags);
  }

  recordHistogram(metricName: string, value: number, tags: Record<string, string> = {}) {
    // Placeholder for metrics
    console.log(`📈 Histogram ${metricName}: ${value}`, tags);
  }

  setGauge(metricName: string, value: number, tags: Record<string, string> = {}) {
    // Placeholder for metrics
    console.log(`📊 Gauge ${metricName}: ${value}`, tags);
  }

  captureException(error: Error, context?: any) {
    console.error('❌ Exception captured:', error, context);

    if (Sentry) {
      Sentry.captureException(error, {
        tags: context,
      });
    }
  }

  captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info', context?: any) {
    console.log(`📝 ${level.toUpperCase()}: ${message}`, context);

    if (Sentry) {
      Sentry.captureMessage(message, level as any);
    }
  }

  setUser(user: { id: string; email: string; org_id?: string }) {
    if (Sentry) {
      Sentry.setUser({
        id: user.id,
        email: user.email,
        org_id: user.org_id,
      });
    }
  }

  setTag(key: string, value: string) {
    if (Sentry) {
      Sentry.setTag(key, value);
    }
  }

  setContext(key: string, context: any) {
    if (Sentry) {
      Sentry.setContext(key, context);
    }
  }
}
