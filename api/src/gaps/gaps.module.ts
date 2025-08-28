import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Gap } from './gap.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Gap])],
  exports: [TypeOrmModule],
})
export class GapsModule {}
