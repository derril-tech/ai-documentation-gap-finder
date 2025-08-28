import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Draft } from './draft.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Draft])],
  exports: [TypeOrmModule],
})
export class DraftsModule {}
