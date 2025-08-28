import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { UsersService } from '../users/users.service';
import { User } from '../users/user.entity';

export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    role: string;
    org_id?: string;
  };
}

@Injectable()
export class AuthService {
  constructor(
    private usersService: UsersService,
    private jwtService: JwtService,
  ) {}

  async validateUser(email: string, password: string): Promise<User | null> {
    try {
      const user = await this.usersService.findByEmail(email);
      if (user && (await bcrypt.compare(password, user.password_hash))) {
        return user;
      }
      return null;
    } catch (error) {
      return null;
    }
  }

  async login(user: User): Promise<AuthResponse> {
    const payload = {
      sub: user.id,
      email: user.email,
      role: user.role,
      org_id: user.org_id,
    };

    return {
      access_token: this.jwtService.sign(payload),
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
        org_id: user.org_id,
      },
    };
  }

  // SSO Stub - In production, integrate with Auth0, Okta, etc.
  async ssoLogin(provider: string, token: string): Promise<AuthResponse> {
    // This is a stub implementation
    // In production, validate the SSO token with the provider
    console.log(`SSO login with ${provider}, token: ${token.substring(0, 20)}...`);

    // For demo purposes, create/find user based on SSO info
    const email = `sso-user@${provider}.com`; // Extract from token in production
    let user = await this.usersService.findByEmail(email);

    if (!user) {
      // Create user if doesn't exist
      user = await this.usersService.create({
        email,
        password_hash: '', // SSO users don't need passwords
        role: 'member',
        org_id: null, // Will be set during org creation
        tz: 'UTC',
      });
    }

    return this.login(user);
  }

  // For development/demo purposes - create demo user
  async createDemoUser(): Promise<User> {
    const demoEmail = 'demo@ai-docgap.com';
    const demoPassword = 'demo123';

    let user = await this.usersService.findByEmail(demoEmail);
    if (!user) {
      const hashedPassword = await bcrypt.hash(demoPassword, 10);
      user = await this.usersService.create({
        email: demoEmail,
        password_hash: hashedPassword,
        role: 'admin',
        org_id: null,
        tz: 'UTC',
      });
    }

    return user;
  }
}
