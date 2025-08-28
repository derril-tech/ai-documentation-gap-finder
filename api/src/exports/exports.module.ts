import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Export } from './export.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Export])],
  exports: [TypeOrmModule],
})
export class ExportsModule {}
