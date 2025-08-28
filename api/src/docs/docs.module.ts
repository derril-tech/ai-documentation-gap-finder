import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Doc } from './doc.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Doc])],
  exports: [TypeOrmModule],
})
export class DocsModule {}
