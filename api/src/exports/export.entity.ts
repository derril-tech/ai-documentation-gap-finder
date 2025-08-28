import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn } from 'typeorm';
import { Project } from '../projects/project.entity';

export type ExportKind = 'pr' | 'bundle';

@Entity('exports')
export class Export {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  project_id: string;

  @ManyToOne(() => Project)
  @JoinColumn({ name: 'project_id' })
  project: Project;

  @Column({
    type: 'enum',
    enum: ['pr', 'bundle'],
  })
  kind: ExportKind;

  @Column({ nullable: true })
  s3_key: string;

  @Column({ nullable: true })
  pr_url: string;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
