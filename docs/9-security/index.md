# Security

Security documentation, hardening guides, and best practices.

## Security Documentation

- **[Security Hardening](hardening.md)** - Production security hardening procedures
- **[Supply Chain Security](supply-chain.md)** - Dependency and supply chain security

## Security Best Practices

### Authentication & Secrets
- Never commit API keys or secrets to repository
- Use environment variables for all credentials
- Rotate secrets regularly
- Use service accounts with minimal permissions

### Code Security
- SQL injection protection via parameterized queries
- Code execution sandboxing with RestrictedPython
- Input validation for all user inputs
- Regular security scanning with Bandit and Safety

### Network Security
- Use TLS/HTTPS for all external communications
- Implement rate limiting on API endpoints
- Use VPC/network isolation in production
- Regular security audits

### Database Security
- Use read-only connections where possible
- Implement row-level security (RLS) in Supabase
- Regular backup verification
- Encrypted connections only

## Security Tools

Run security checks:
```bash
make security          # Run all security checks
bandit -r src/         # Python security linting
safety check          # Dependency vulnerability scanning
pip-audit             # Audit installed packages
```

## Reporting Security Issues

If you discover a security vulnerability, please email security@[yourdomain] with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

**Do not** open public issues for security vulnerabilities.

## Quick Links

- [Back to Documentation Home](../README.md)
- [Deployment](../6-deployment/index.md)
- [Operations](../7-operations/index.md)
