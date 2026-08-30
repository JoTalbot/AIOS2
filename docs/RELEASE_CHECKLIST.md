# AIOS2 Release Checklist

## Installation
- [ ] Python 3.11+ available
- [ ] Dependencies installed
- [ ] Environment variables configured

## Startup Validation
- [ ] Application starts successfully
- [ ] API entrypoint loads
- [ ] Runtime validation passes

## Service Validation
- [ ] `/health` returns OK
- [ ] `/ready` returns ready
- [ ] `/diagnostics` returns operational state
- [ ] `/system/status` returns unified operational report

## Regression
- [ ] Run `pytest tests -q`
- [ ] Security tests pass
- [ ] Recovery tests pass
- [ ] Production smoke tests pass

## Deployment
- [ ] Docker build succeeds
- [ ] Docker Compose deployment verified
- [ ] Rollback procedure documented

## Release Sign-off
- [ ] Documentation reviewed
- [ ] CI pipeline green
- [ ] Release approved
