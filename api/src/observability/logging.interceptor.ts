import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ObservabilityService } from './observability.service';
import { TelemetryService } from '../telemetry/telemetry.service';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  constructor(
    private readonly observabilityService: ObservabilityService,
    private readonly telemetryService: TelemetryService
  ) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const response = context.switchToHttp().getResponse();
    const startTime = Date.now();

    const { method, url, body, query, params } = request;
    const userAgent = request.get('User-Agent') || '';
    const ip = request.ip || request.connection?.remoteAddress || '';

    // Log incoming request
    console.log(`📨 ${method} ${url}`, {
      userAgent,
      ip,
      body: this.sanitizeBody(body),
      query,
      params,
    });

    // Set user context for observability
    if (request.user) {
      this.observabilityService.setUser(request.user);
      this.observabilityService.setContext('request', {
        method,
        url,
        userId: request.user.id,
        orgId: request.user.org_id,
      });
    }

    return next.handle().pipe(
      tap(async (data) => {
        const duration = Date.now() - startTime;
        const statusCode = response.statusCode;

        // Log response
        console.log(`📤 ${method} ${url} ${statusCode} - ${duration}ms`);

        // Track endpoint usage with telemetry
        try {
          await this.telemetryService.trackEndpointUsage(
            url.split('?')[0], // Remove query params
            method,
            statusCode,
            duration,
            request.user?.id,
            request.user?.org_id,
            request.headers['content-length'] ? parseInt(request.headers['content-length']) : undefined,
            response.get('content-length') ? parseInt(response.get('content-length')) : undefined,
            statusCode >= 400 ? 'Request failed' : undefined,
            userAgent,
            ip
          );
        } catch (error) {
          console.error('Failed to track telemetry:', error);
        }

        // Record metrics
        this.observabilityService.incrementCounter('api_requests_total', 1, {
          method,
          status_code: statusCode.toString(),
          endpoint: url.split('?')[0], // Remove query params
        });

        this.observabilityService.recordHistogram('api_request_duration', duration, {
          method,
          endpoint: url.split('?')[0],
        });

        // Set tags for Sentry
        this.observabilityService.setTag('endpoint', url);
        this.observabilityService.setTag('method', method);
        this.observabilityService.setTag('status_code', statusCode.toString());
      }),
    );
  }

  private sanitizeBody(body: any): any {
    if (!body) return body;

    const sensitiveFields = ['password', 'token', 'secret', 'key', 'authorization'];
    const sanitized = { ...body };

    for (const field of sensitiveFields) {
      if (sanitized[field]) {
        sanitized[field] = '[REDACTED]';
      }
    }

    return sanitized;
  }
}
