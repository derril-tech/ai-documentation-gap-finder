import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Project } from './project.entity';
import { OrganizationsService } from '../organizations/organizations.service';
import { UsersService } from '../users/users.service';

export interface CreateProjectDto {
  name: string;
  code_repo?: string;
  docs_repo?: string;
  default_branch?: string;
}

@Injectable()
export class ProjectsService {
  constructor(
    @InjectRepository(Project)
    private projectsRepository: Repository<Project>,
    private organizationsService: OrganizationsService,
    private usersService: UsersService,
  ) {}

  async findAll(): Promise<Project[]> {
    return this.projectsRepository.find({
      relations: ['organization'],
    });
  }

  async findById(id: string): Promise<Project> {
    const project = await this.projectsRepository.findOne({
      where: { id },
      relations: ['organization'],
    });

    if (!project) {
      throw new NotFoundException(`Project with ID ${id} not found`);
    }

    return project;
  }

  async findByOrgId(orgId: string): Promise<Project[]> {
    return this.projectsRepository.find({
      where: { org_id: orgId },
      relations: ['organization'],
    });
  }

  async create(createProjectDto: CreateProjectDto, userId: string): Promise<Project> {
    // Get user's organization
    const user = await this.usersService.findById(userId);
    if (!user.org_id) {
      throw new ForbiddenException('User must belong to an organization to create projects');
    }

    // Check if user can create projects in this organization
    const canCreate = await this.usersService.canManageUsers(userId, user.org_id);
    if (!canCreate) {
      throw new ForbiddenException('Insufficient permissions to create projects');
    }

    const project = this.projectsRepository.create({
      ...createProjectDto,
      org_id: user.org_id,
      default_branch: createProjectDto.default_branch || 'main',
    });

    return this.projectsRepository.save(project);
  }

  async update(id: string, updateProjectDto: Partial<CreateProjectDto>, userId: string): Promise<Project> {
    const project = await this.findById(id);

    // Check if user can update this project
    const canUpdate = await this.checkProjectAccess(userId, project.org_id);
    if (!canUpdate) {
      throw new ForbiddenException('Insufficient permissions to update this project');
    }

    await this.projectsRepository.update(id, updateProjectDto);
    return this.findById(id);
  }

  async remove(id: string, userId: string): Promise<void> {
    const project = await this.findById(id);

    // Check if user can delete this project
    const canDelete = await this.checkProjectAccess(userId, project.org_id, true);
    if (!canDelete) {
      throw new ForbiddenException('Insufficient permissions to delete this project');
    }

    const result = await this.projectsRepository.delete(id);
    if (result.affected === 0) {
      throw new NotFoundException(`Project with ID ${id} not found`);
    }
  }

  // RBAC helper methods
  private async checkProjectAccess(userId: string, orgId: string, requireAdmin = false): Promise<boolean> {
    const user = await this.usersService.findById(userId);

    // User must belong to the same organization
    if (user.org_id !== orgId) {
      return false;
    }

    // If admin access is required, check user's role
    if (requireAdmin) {
      return await this.usersService.isAdmin(userId);
    }

    // For basic access, any member of the org can access
    return true;
  }

  async canUserAccessProject(userId: string, projectId: string): Promise<boolean> {
    try {
      const project = await this.findById(projectId);
      return await this.checkProjectAccess(userId, project.org_id);
    } catch {
      return false;
    }
  }
}
