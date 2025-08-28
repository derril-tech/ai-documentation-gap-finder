import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Score } from './score.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Score])],
  exports: [TypeOrmModule],
})
export class ScoresModule {}
