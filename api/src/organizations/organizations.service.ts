import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Organization } from './organization.entity';

export interface CreateOrganizationDto {
  name: string;
  plan?: 'free' | 'pro' | 'enterprise';
}

@Injectable()
export class OrganizationsService {
  constructor(
    @InjectRepository(Organization)
    private organizationsRepository: Repository<Organization>,
  ) {}

  async findAll(): Promise<Organization[]> {
    return this.organizationsRepository.find({
      relations: ['users', 'projects'],
    });
  }

  async findById(id: string): Promise<Organization> {
    const organization = await this.organizationsRepository.findOne({
      where: { id },
      relations: ['users', 'projects'],
    });

    if (!organization) {
      throw new NotFoundException(`Organization with ID ${id} not found`);
    }

    return organization;
  }

  async findByUserId(userId: string): Promise<Organization | null> {
    return this.organizationsRepository
      .createQueryBuilder('org')
      .leftJoin('org.users', 'user')
      .where('user.id = :userId', { userId })
      .getOne();
  }

  async create(createOrgDto: CreateOrganizationDto): Promise<Organization> {
    const organization = this.organizationsRepository.create({
      ...createOrgDto,
      plan: createOrgDto.plan || 'pro',
    });
    return this.organizationsRepository.save(organization);
  }

  async update(id: string, updateOrgDto: Partial<CreateOrganizationDto>): Promise<Organization> {
    await this.organizationsRepository.update(id, updateOrgDto);
    return this.findById(id);
  }

  async remove(id: string): Promise<void> {
    const result = await this.organizationsRepository.delete(id);
    if (result.affected === 0) {
      throw new NotFoundException(`Organization with ID ${id} not found`);
    }
  }

  // RBAC helpers
  async canUserAccess(userId: string, orgId: string): Promise<boolean> {
    const organization = await this.findById(orgId);
    return organization.users.some(user => user.id === userId);
  }

  async getUserRole(userId: string, orgId: string): Promise<string | null> {
    const organization = await this.findById(orgId);
    const user = organization.users.find(u => u.id === userId);
    return user ? user.role : null;
  }
}
