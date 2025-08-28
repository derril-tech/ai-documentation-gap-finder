import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { Project } from '../projects/project.entity';
import { CodeEntity } from '../entities/entity.entity';
import { Doc } from '../docs/doc.entity';

export type GapType = 'missing' | 'partial' | 'stale' | 'broken_link' | 'incorrect_sample' | 'orphan_doc' | 'outdated_screenshot';
export type GapSeverity = 'low' | 'medium' | 'high' | 'critical';
export type GapStatus = 'open' | 'investigating' | 'resolved' | 'wont_fix';

@Entity('gaps')
export class Gap {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column({
    type: 'enum',
    enum: ['missing', 'partial', 'stale', 'broken_link', 'incorrect_sample', 'orphan_doc', 'outdated_screenshot'],
  })
  type: GapType;

  @Column({ nullable: true })
  entity_id: string;

  @ManyToOne(() => CodeEntity, { nullable: true })
  @JoinColumn({ name: 'entity_id' })
  entity: CodeEntity;

  @Column({ nullable: true })
  doc_id: string;

  @ManyToOne(() => Doc, { nullable: true })
  @JoinColumn({ name: 'doc_id' })
  doc: Doc;

  @Column({
    type: 'enum',
    enum: ['low', 'medium', 'high', 'critical'],
    default: 'medium',
  })
  severity: GapSeverity;

  @Column({ type: 'numeric', default: 0 })
  priority: number;

  @Column({ type: 'text', nullable: true })
  reason: string;

  @Column({
    type: 'enum',
    enum: ['open', 'investigating', 'resolved', 'wont_fix'],
    default: 'open',
  })
  status: GapStatus;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updated_at: Date;
}
