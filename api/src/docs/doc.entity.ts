import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn, UpdateDateColumn, Index } from 'typeorm';
import { Project } from '../projects/project.entity';

@Entity('docs')
export class Doc {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column()
  path: string;

  @Column({ nullable: true })
  title: string;

  @Column({ type: 'jsonb', default: '[]' })
  headings: any[];

  @Column({ type: 'jsonb', default: '[]' })
  links: any[];

  @Column({ nullable: true })
  last_commit: string;

  @Column({ type: 'timestamptz', nullable: true })
  last_updated: Date;

  @Column({ type: 'jsonb', default: '{}' })
  frontmatter: any;

  @Column({ type: 'vector', length: 1536, nullable: true })
  @Index()
  embedding: number[];

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
