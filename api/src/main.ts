import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import helmet from 'helmet';
import compression from 'compression';
import { AppModule } from './app.module';
import { GlobalExceptionFilter } from './observability/global-exception.filter';
import { LoggingInterceptor } from './observability/logging.interceptor';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Security
  app.use(helmet());
  app.use(compression());

  // CORS
  app.enableCors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
  });

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  // Global prefix
  app.setGlobalPrefix('v1');

  // Global exception filter
  app.useGlobalFilters(new GlobalExceptionFilter(app.get('ObservabilityService')));

  // Global interceptor for logging
  app.useGlobalInterceptors(new LoggingInterceptor(app.get('ObservabilityService')));

  // Swagger documentation
  const config = new DocumentBuilder()
    .setTitle('AI Documentation Gap Finder API')
    .setDescription('API for detecting documentation gaps using AI')
    .setVersion('1.0')
    .addTag('auth', 'Authentication endpoints')
    .addTag('organizations', 'Organization management')
    .addTag('projects', 'Project management')
    .addTag('gaps', 'Gap detection and scoring')
    .addTag('drafts', 'Auto-drafting functionality')
    .addTag('exports', 'Export functionality')
    .addBearerAuth()
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api', app, document);

  const port = process.env.API_PORT || 4000;
  await app.listen(port);

  console.log(`🚀 AI Documentation Gap Finder API running on port ${port}`);
  console.log(`📖 API documentation available at http://localhost:${port}/api`);
}

bootstrap();
