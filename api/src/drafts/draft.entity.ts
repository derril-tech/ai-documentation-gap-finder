import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { Project } from '../projects/project.entity';
import { Doc } from '../docs/doc.entity';
import { CodeEntity } from '../entities/entity.entity';

export type DraftStatus = 'pending' | 'approved' | 'rejected' | 'merged';

@Entity('drafts')
export class Draft {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column({ nullable: true })
  doc_id: string;

  @ManyToOne(() => Doc, { nullable: true })
  @JoinColumn({ name: 'doc_id' })
  doc: Doc;

  @Column({ nullable: true })
  entity_id: string;

  @ManyToOne(() => CodeEntity, { nullable: true })
  @JoinColumn({ name: 'entity_id' })
  entity: CodeEntity;

  @Column({ type: 'text', nullable: true })
  mdx: string;

  @Column({ type: 'jsonb', default: '{}' })
  rationale: any;

  @Column({
    type: 'enum',
    enum: ['pending', 'approved', 'rejected', 'merged'],
    default: 'pending',
  })
  status: DraftStatus;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updated_at: Date;
}
