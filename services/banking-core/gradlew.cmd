@echo off
setlocal

set GRADLE_USER_HOME=%TEMP%\banking-core-gradle-cache
set BANKING_CORE_BUILD_DIR=%TEMP%\banking-core-build-%RANDOM%
set GRADLE_HOME=C:\Gradle\gradle-8.10
set GRADLE_CLI_JAR=%GRADLE_HOME%\lib\gradle-gradle-cli-main-8.10.jar

if not exist "%GRADLE_CLI_JAR%" (
  echo Gradle 8.10 was not found at %GRADLE_HOME%.
  echo Install Gradle or update GRADLE_HOME in services\banking-core\gradlew.cmd.
  exit /b 1
)

java ^
  -Xmx1024m ^
  -Dorg.gradle.native=false ^
  -Dorg.gradle.appname=gradle ^
  -classpath "%GRADLE_CLI_JAR%" ^
  org.gradle.launcher.GradleMain ^
  --no-daemon ^
  --no-watch-fs ^
  --project-cache-dir "%TEMP%\banking-core-gradle-project-cache" ^
  %*

exit /b %ERRORLEVEL%
