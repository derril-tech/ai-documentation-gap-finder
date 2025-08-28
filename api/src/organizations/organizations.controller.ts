import { Controller, Get, Post, Body, Param, Put, Delete, UseGuards, Request } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { OrganizationsService } from './organizations.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { UsersService } from '../users/users.service';

class CreateOrganizationDto {
  name: string;
  plan?: 'free' | 'pro' | 'enterprise';
}

@ApiTags('organizations')
@Controller('organizations')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class OrganizationsController {
  constructor(
    private organizationsService: OrganizationsService,
    private usersService: UsersService,
  ) {}

  @Get()
  @ApiOperation({ summary: 'Get all organizations' })
  @ApiResponse({ status: 200, description: 'Organizations retrieved successfully' })
  async findAll() {
    return this.organizationsService.findAll();
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get organization by ID' })
  @ApiResponse({ status: 200, description: 'Organization retrieved successfully' })
  @ApiResponse({ status: 404, description: 'Organization not found' })
  async findById(@Param('id') id: string) {
    return this.organizationsService.findById(id);
  }

  @Post()
  @ApiOperation({ summary: 'Create new organization' })
  @ApiResponse({ status: 201, description: 'Organization created successfully' })
  async create(@Body() createOrgDto: CreateOrganizationDto, @Request() req) {
    const organization = await this.organizationsService.create(createOrgDto);

    // Assign current user as owner of the new organization
    await this.usersService.update(req.user.id, {
      org_id: organization.id,
      role: 'owner',
    });

    return organization;
  }

  @Put(':id')
  @ApiOperation({ summary: 'Update organization' })
  @ApiResponse({ status: 200, description: 'Organization updated successfully' })
  async update(@Param('id') id: string, @Body() updateOrgDto: Partial<CreateOrganizationDto>) {
    return this.organizationsService.update(id, updateOrgDto);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete organization' })
  @ApiResponse({ status: 200, description: 'Organization deleted successfully' })
  async remove(@Param('id') id: string) {
    await this.organizationsService.remove(id);
    return { message: 'Organization deleted successfully' };
  }

  @Get(':id/users')
  @ApiOperation({ summary: 'Get users in organization' })
  @ApiResponse({ status: 200, description: 'Users retrieved successfully' })
  async getUsers(@Param('id') id: string) {
    const organization = await this.organizationsService.findById(id);
    return organization.users;
  }
}
