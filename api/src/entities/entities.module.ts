import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { CodeEntity } from './entity.entity';

@Module({
  imports: [TypeOrmModule.forFeature([CodeEntity])],
  exports: [TypeOrmModule],
})
export class EntitiesModule {}
