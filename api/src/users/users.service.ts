import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';

export interface CreateUserDto {
  email: string;
  password_hash: string;
  role: 'owner' | 'admin' | 'member';
  org_id: string | null;
  tz: string;
}

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private usersRepository: Repository<User>,
  ) {}

  async findAll(): Promise<User[]> {
    return this.usersRepository.find({
      relations: ['organization'],
    });
  }

  async findById(id: string): Promise<User> {
    const user = await this.usersRepository.findOne({
      where: { id },
      relations: ['organization'],
    });

    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }

    return user;
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.usersRepository.findOne({
      where: { email },
      relations: ['organization'],
    });
  }

  async findByOrgId(orgId: string): Promise<User[]> {
    return this.usersRepository.find({
      where: { org_id: orgId },
      relations: ['organization'],
    });
  }

  async create(createUserDto: CreateUserDto): Promise<User> {
    const user = this.usersRepository.create(createUserDto);
    return this.usersRepository.save(user);
  }

  async update(id: string, updateUserDto: Partial<CreateUserDto>): Promise<User> {
    await this.usersRepository.update(id, updateUserDto);
    return this.findById(id);
  }

  async remove(id: string): Promise<void> {
    const result = await this.usersRepository.delete(id);
    if (result.affected === 0) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
  }

  // RBAC helper methods
  async isOwner(userId: string): Promise<boolean> {
    const user = await this.findById(userId);
    return user.role === 'owner';
  }

  async isAdmin(userId: string): Promise<boolean> {
    const user = await this.findById(userId);
    return user.role === 'admin' || user.role === 'owner';
  }

  async canAccessOrganization(userId: string, orgId: string): Promise<boolean> {
    const user = await this.findById(userId);
    return user.org_id === orgId;
  }

  async canManageUsers(userId: string, targetOrgId: string): Promise<boolean> {
    const user = await this.findById(userId);
    return user.org_id === targetOrgId && (user.role === 'admin' || user.role === 'owner');
  }
}
