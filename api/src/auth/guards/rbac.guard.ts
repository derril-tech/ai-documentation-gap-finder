import { Injectable, CanActivate, ExecutionContext, ForbiddenException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { UsersService } from '../../users/users.service';
import { OrganizationsService } from '../../organizations/organizations.service';

export interface RbacOptions {
  roles?: ('owner' | 'admin' | 'member')[];
  requireOrgMember?: boolean;
  requireOrgAdmin?: boolean;
}

@Injectable()
export class RbacGuard implements CanActivate {
  constructor(
    private reflector: Reflector,
    private usersService: UsersService,
    private organizationsService: OrganizationsService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user) {
      throw new ForbiddenException('User not authenticated');
    }

    // Get RBAC options from metadata
    const rbacOptions = this.reflector.get<RbacOptions>('rbac', context.getHandler());

    if (!rbacOptions) {
      // No RBAC requirements, allow access
      return true;
    }

    // Check role requirements
    if (rbacOptions.roles && rbacOptions.roles.length > 0) {
      if (!rbacOptions.roles.includes(user.role)) {
        throw new ForbiddenException('Insufficient role permissions');
      }
    }

    // Check organization membership requirement
    if (rbacOptions.requireOrgMember) {
      if (!user.org_id) {
        throw new ForbiddenException('User must belong to an organization');
      }
    }

    // Check organization admin requirement
    if (rbacOptions.requireOrgAdmin) {
      const isAdmin = await this.usersService.isAdmin(user.id);
      if (!isAdmin) {
        throw new ForbiddenException('Organization admin access required');
      }
    }

    return true;
  }
}
