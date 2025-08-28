import { Controller, Request, Post, UseGuards, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { AuthService, AuthResponse } from './auth.service';
import { LocalAuthGuard } from './guards/local-auth.guard';
import { JwtAuthGuard } from './guards/jwt-auth.guard';

class LoginDto {
  email: string;
  password: string;
}

class SsoLoginDto {
  provider: string;
  token: string;
}

@ApiTags('auth')
@Controller('auth')
export class AuthController {
  constructor(private authService: AuthService) {}

  @UseGuards(LocalAuthGuard)
  @Post('login')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Login with email and password' })
  @ApiResponse({ status: 200, description: 'Login successful' })
  @ApiResponse({ status: 401, description: 'Invalid credentials' })
  async login(@Request() req, @Body() loginDto: LoginDto): Promise<AuthResponse> {
    return this.authService.login(req.user);
  }

  @Post('sso')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'SSO login (stub implementation)' })
  @ApiResponse({ status: 200, description: 'SSO login successful' })
  async ssoLogin(@Body() ssoDto: SsoLoginDto): Promise<AuthResponse> {
    return this.authService.ssoLogin(ssoDto.provider, ssoDto.token);
  }

  @UseGuards(JwtAuthGuard)
  @Post('refresh')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Refresh JWT token' })
  @ApiResponse({ status: 200, description: 'Token refreshed' })
  @ApiBearerAuth()
  async refresh(@Request() req): Promise<AuthResponse> {
    return this.authService.login(req.user);
  }

  @UseGuards(JwtAuthGuard)
  @Post('me')
  @ApiOperation({ summary: 'Get current user info' })
  @ApiResponse({ status: 200, description: 'User info retrieved' })
  @ApiBearerAuth()
  async me(@Request() req): Promise<any> {
    return {
      id: req.user.id,
      email: req.user.email,
      role: req.user.role,
      org_id: req.user.org_id,
    };
  }

  @Post('demo')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Create/login demo user (development only)' })
  @ApiResponse({ status: 200, description: 'Demo user created/logged in' })
  async createDemoUser(): Promise<AuthResponse> {
    const user = await this.authService.createDemoUser();
    return this.authService.login(user);
  }
}
