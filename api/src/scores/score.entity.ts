import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn } from 'typeorm';
import { Project } from '../projects/project.entity';
import { Doc } from '../docs/doc.entity';

@Entity('scores')
export class Score {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column()
  doc_id: string;

  @ManyToOne(() => Doc)
  @JoinColumn({ name: 'doc_id' })
  doc: Doc;

  @Column({ type: 'numeric', precision: 3, scale: 2, nullable: true })
  clarity: number;

  @Column({ type: 'numeric', precision: 3, scale: 2, nullable: true })
  completeness: number;

  @Column({ type: 'numeric', precision: 3, scale: 2, nullable: true })
  freshness: number;

  @Column({ type: 'numeric', precision: 3, scale: 2, nullable: true })
  example_density: number;

  @Column({ type: 'jsonb', default: '{}' })
  meta: any;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
