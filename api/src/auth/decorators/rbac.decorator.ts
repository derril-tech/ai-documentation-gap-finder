import { SetMetadata } from '@nestjs/common';
import { RbacOptions } from '../guards/rbac.guard';

export const Rbac = (options: RbacOptions) => SetMetadata('rbac', options);
