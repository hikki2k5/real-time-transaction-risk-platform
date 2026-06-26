plugins {
    java
    application
    id("org.springframework.boot") version "3.3.5"
    id("io.spring.dependency-management") version "1.1.6"
}

group = "com.example.fraud"
version = "0.1.0-SNAPSHOT"

val bankingCoreBuildDir = System.getenv("BANKING_CORE_BUILD_DIR")
if (!bankingCoreBuildDir.isNullOrBlank()) {
    layout.buildDirectory.set(file(bankingCoreBuildDir))
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

application {
    mainClass.set("com.example.fraud.bankingcore.BankingCoreApplication")
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.kafka:spring-kafka")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
}

tasks.test {
    useJUnitPlatform()
}
