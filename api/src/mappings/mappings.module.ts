import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Mapping } from './mapping.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Mapping])],
  exports: [TypeOrmModule],
})
export class MappingsModule {}
