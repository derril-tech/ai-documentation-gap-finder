import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn, Index } from 'typeorm';
import { Project } from '../projects/project.entity';

export type EntityKind = 'function' | 'class' | 'endpoint' | 'cli' | 'flag' | 'env' | 'type';
export type EntityVisibility = 'public' | 'private' | 'internal';

@Entity('entities')
export class CodeEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column({
    type: 'enum',
    enum: ['function', 'class', 'endpoint', 'cli', 'flag', 'env', 'type'],
  })
  kind: EntityKind;

  @Column()
  name: string;

  @Column({ nullable: true })
  path: string;

  @Column({ nullable: true })
  lang: string;

  @Column({ type: 'jsonb', nullable: true })
  signature: any;

  @Column({ type: 'jsonb', nullable: true })
  spec: any;

  @Column({
    type: 'enum',
    enum: ['public', 'private', 'internal'],
    default: 'private',
  })
  visibility: EntityVisibility;

  @Column({ nullable: true })
  version: string;

  @Column({ type: 'vector', length: 1536, nullable: true })
  @Index()
  embedding: number[];

  @Column({ type: 'jsonb', default: '{}' })
  meta: any;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
