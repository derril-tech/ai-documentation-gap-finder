import { Entity, Column, PrimaryGeneratedColumn, OneToMany, CreateDateColumn } from 'typeorm';
import { User } from '../users/user.entity';
import { Project } from '../projects/project.entity';

export type OrganizationPlan = 'free' | 'pro' | 'enterprise';

@Entity('orgs')
export class Organization {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  name: string;

  @Column({
    type: 'enum',
    enum: ['free', 'pro', 'enterprise'],
    default: 'pro',
  })
  plan: OrganizationPlan;

  @OneToMany(() => User, user => user.organization)
  users: User[];

  @OneToMany(() => Project, project => project.organization)
  projects: Project[];

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
