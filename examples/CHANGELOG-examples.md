# Examples Directory - Changelog

## Updates Applied

### Fixed Inconsistencies
1. **Filename References**: All usage examples now reference the correct filenames:
   - `monitoring-options.txt` → `climb-options-monitoring.txt`
   - `reports-options.txt` → `climb-options-reports.txt`

### Enhanced Documentation

#### Environment Variable Storage
- Added guidance on persistent storage of `CLIMB_PASSWORD`:
  - `/etc/environment` for system-wide persistence
  - systemd service `Environment=` directive
  - Session-level `export` command

#### SMTP Port Selection
- Added comprehensive port selection guide in README-options.md:
  - Port 587 (STARTTLS - recommended)
  - Port 465 (SMTPS - SSL from start)
  - Port 25 (unencrypted - legacy only)
- Added port comments to monitoring and reports templates

#### Testing Improvements
- Added "Test without sending" examples in all templates
- Added authentication validation pattern: `-output /dev/null`
- Enhanced verbose testing documentation
- Added exit code checking examples

### Files Modified
- `climb-options-monitoring.txt` - Fixed filenames, added port/env var docs, added test example
- `climb-options-reports.txt` - Fixed filenames, added port/env var docs, added test example
- `README-options.md` - Enhanced testing section, added port selection guide, improved env var docs

### Summary
All example files now have:
- ✅ Consistent filename references
- ✅ Clear SMTP port selection guidance
- ✅ Environment variable persistence options
- ✅ Testing examples without sending mail
- ✅ Authentication validation patterns
