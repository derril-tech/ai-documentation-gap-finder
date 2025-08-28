import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn } from 'typeorm';
import { Organization } from '../organizations/organization.entity';

@Entity('projects')
export class Project {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  org_id: string;

  @ManyToOne(() => Organization)
  @JoinColumn({ name: 'org_id' })
  organization: Organization;

  @Column()
  name: string;

  @Column({ nullable: true })
  code_repo: string;

  @Column({ nullable: true })
  docs_repo: string;

  @Column({ default: 'main' })
  default_branch: string;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
