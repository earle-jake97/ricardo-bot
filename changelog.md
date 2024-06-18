# Changelog
## [1.1.2] - 2024-06-17
### Fixed
- Damage calculations should be accurate and will not give you a negative balance when overkilling the boss.

## [1.1.1] - 2024-06-17
### Changed
- Leaderboard responses will only be shown to those who called it.
- Critical hits are now more notable with an emoji💥

## [1.1.0] - 2024-06-17
### Added
- Users now have a crit rate and crit damage modifier.
- /profile - you can now view your own or other user profiles and view their stats.

### Changed
- Changed how damage calculation works.
- Added many more options to config.json

### Fixed
- Can no longer go negative when refunding crit vbucks
- No more variable names in command descriptions

### Planned 
- Shop - will allow users to purchase items that aid their income and damage in some way.

# Changelog
## [1.0.6] - 2024-06-15
### Changed
- More refactoring and config options added

## [1.0.5] - 2024-06-15
### Changed
- More refactoring. Extra config options added.

## [1.0.4] - 2024-06-15
### Changed
- First iteration of refactoring code has been done.

### Fixed
- You no longer lose extra Vbucks for critting Ricardo.

## [1.0.3] - 2024-06-14
### Added
- Added Participation and Participation Points. Gain PP from contributing to Ricardo kills and add to your income based on your PP.
### Changed
- Income is now a static 18 + however many extra Vbucks you would earn from PP.

### Fixed
- Fixed ugly formatting on /leaderboards command
- Last ID in database no longer loses Vbucks for someone else's kill.

## [1.0.2] - 2024-06-14
### Changed
- You can now specify "all" to use your entire balance to kill Ricardo.

### Fixed
- Killing Ricardo now properly mentions him.


## [1.0.1] - 2024-06-14
### Added
- You can now critically strike Ricardo. Crits have a 10% chance to occur and deal 1.5x damage.


## [1.0.0] - 2024-06-13
### Changed
- Ricardo HP growth per death has been nerfed from 15% -> 5%

### Fixed
- Fixed an issue where Ricardo could be overkilled and not refund you the remaining balance.
