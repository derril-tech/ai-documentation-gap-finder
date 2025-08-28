import { Entity, Column, PrimaryGeneratedColumn, ManyToOne, JoinColumn, CreateDateColumn } from 'typeorm';
import { Organization } from '../organizations/organization.entity';

export type UserRole = 'owner' | 'admin' | 'member';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ unique: true })
  email: string;

  @Column({ name: 'password_hash' })
  password_hash: string;

  @Column({
    type: 'enum',
    enum: ['owner', 'admin', 'member'],
    default: 'member',
  })
  role: UserRole;

  @Column({ nullable: true })
  org_id: string;

  @ManyToOne(() => Organization, { nullable: true })
  @JoinColumn({ name: 'org_id' })
  organization: Organization;

  @Column({ default: 'UTC' })
  tz: string;

  @CreateDateColumn({ name: 'created_at' })
  created_at: Date;
}
