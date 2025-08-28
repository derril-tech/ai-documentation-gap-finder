import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn } from 'typeorm';
import { Project } from '../projects/project.entity';
import { CodeEntity } from '../entities/entity.entity';
import { Doc } from '../docs/doc.entity';

export type RelationType = 'describes' | 'references' | 'mentions';

@Entity('mappings')
export class Mapping {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column()
  entity_id: string;

  @ManyToOne(() => CodeEntity)
  @JoinColumn({ name: 'entity_id' })
  entity: CodeEntity;

  @Column()
  doc_id: string;

  @ManyToOne(() => Doc)
  @JoinColumn({ name: 'doc_id' })
  doc: Doc;

  @Column({ nullable: true })
  anchor: string;

  @Column({ type: 'numeric', precision: 3, scale: 2, nullable: true })
  score: number;

  @Column({
    type: 'enum',
    enum: ['describes', 'references', 'mentions'],
  })
  relation: RelationType;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
