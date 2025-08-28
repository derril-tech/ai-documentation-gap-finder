import { Controller, Get, Post, Body, Param, Put, Delete, UseGuards, Request } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { ProjectsService } from './projects.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

class CreateProjectDto {
  name: string;
  code_repo?: string;
  docs_repo?: string;
  default_branch?: string;
}

@ApiTags('projects')
@Controller('projects')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class ProjectsController {
  constructor(private projectsService: ProjectsService) {}

  @Get()
  @ApiOperation({ summary: 'Get all projects' })
  @ApiResponse({ status: 200, description: 'Projects retrieved successfully' })
  async findAll(@Request() req) {
    // Filter projects by user's organization
    const userId = req.user.id;
    // In a real implementation, you'd filter by user's org
    // For now, return all projects
    return this.projectsService.findAll();
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get project by ID' })
  @ApiResponse({ status: 200, description: 'Project retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Project not found' })
  async findById(@Param('id') id: string, @Request() req) {
    const canAccess = await this.projectsService.canUserAccessProject(req.user.id, id);
    if (!canAccess) {
      throw new Error('Access denied');
    }
    return this.projectsService.findById(id);
  }

  @Post()
  @ApiOperation({ summary: 'Create new project' })
  @ApiResponse({ status: 201, description: 'Project created successfully' })
  async create(@Body() createProjectDto: CreateProjectDto, @Request() req) {
    return this.projectsService.create(createProjectDto, req.user.id);
  }

  @Put(':id')
  @ApiOperation({ summary: 'Update project' })
  @ApiResponse({ status: 200, description: 'Project updated successfully' })
  async update(@Param('id') id: string, @Body() updateProjectDto: Partial<CreateProjectDto>, @Request() req) {
    return this.projectsService.update(id, updateProjectDto, req.user.id);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete project' })
  @ApiResponse({ status: 200, description: 'Project deleted successfully' })
  async remove(@Param('id') id: string, @Request() req) {
    await this.projectsService.remove(id, req.user.id);
    return { message: 'Project deleted successfully' };
  }

  @Get('org/:orgId')
  @ApiOperation({ summary: 'Get projects by organization' })
  @ApiResponse({ status: 200, description: 'Projects retrieved successfully' })
  async findByOrgId(@Param('orgId') orgId: string, @Request() req) {
    // Check if user can access this organization's projects
    // In a real implementation, you'd check org membership
    return this.projectsService.findByOrgId(orgId);
  }
}
