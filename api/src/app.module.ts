import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { OrganizationsModule } from './organizations/organizations.module';
import { ProjectsModule } from './projects/projects.module';
import { EntitiesModule } from './entities/entities.module';
import { DocsModule } from './docs/docs.module';
import { MappingsModule } from './mappings/mappings.module';
import { GapsModule } from './gaps/gaps.module';
import { ScoresModule } from './scores/scores.module';
import { DraftsModule } from './drafts/drafts.module';
import { ExportsModule } from './exports/exports.module';
import { ObservabilityModule } from './observability/observability.module';
import { TelemetryModule } from './telemetry/telemetry.module';
import { CodeEntity } from './entities/entity.entity';
import { Doc } from './docs/doc.entity';
import { Mapping } from './mappings/mapping.entity';
import { Gap } from './gaps/gap.entity';
import { Score } from './scores/score.entity';
import { Draft } from './drafts/draft.entity';
import { Export } from './exports/export.entity';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env'],
    }),
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: process.env.POSTGRES_HOST || 'localhost',
      port: parseInt(process.env.POSTGRES_PORT || '5432'),
      username: process.env.POSTGRES_USER || 'postgres',
      password: process.env.POSTGRES_PASSWORD || 'postgres',
      database: process.env.POSTGRES_DB || 'ai_docgap',
      entities: [
        __dirname + '/**/*.entity{.ts,.js}',
        CodeEntity,
        Doc,
        Mapping,
        Gap,
        Score,
        Draft,
        Export,
      ],
      synchronize: process.env.NODE_ENV === 'development', // Use migrations in production
      logging: process.env.NODE_ENV === 'development',
      ssl: process.env.NODE_ENV === 'production',
    }),
    AuthModule,
    UsersModule,
    OrganizationsModule,
    ProjectsModule,
    EntitiesModule,
    DocsModule,
    MappingsModule,
    GapsModule,
    ScoresModule,
    DraftsModule,
    ExportsModule,
    ObservabilityModule,
    TelemetryModule,
  ],
})
export class AppModule {}
