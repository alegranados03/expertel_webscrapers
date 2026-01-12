# Plan de Deployment: ExpertelIQ Webscrapers

## Resumen Ejecutivo

Infraestructura AWS para ejecutar webscrapers con interfaz gráfica accesible remotamente.

| Aspecto | Configuración |
|---------|---------------|
| **Tipo de instancia** | EC2 t3.medium (Ubuntu 22.04) |
| **Acceso remoto** | noVNC via HTTPS (autenticación requerida) |
| **Ejecuciones programadas** | 23:00 EST y 12:00 EST diariamente |
| **Notificaciones** | Email + Slack + Teams |
| **CI/CD** | AWS CodeBuild (push a branch → deploy automático) |
| **Repositorio** | https://github.com/alegranados03/expertel_webscrapers.git |

---

## Arquitectura

```
                         Internet
                             │
                             ▼
    ┌────────────────────────────────────────────────────────────────┐
    │                    VPC (experteliq2-{env})                     │
    │  ┌──────────────────────────────────────────────────────────┐  │
    │  │                     Public Subnet                         │  │
    │  │                                                           │  │
    │  │  ┌─────────────────────────────────────────────────────┐  │  │
    │  │  │  EC2 Scraper Instance (t3.medium)                   │  │  │
    │  │  │  ┌───────────────────────────────────────────────┐  │  │  │
    │  │  │  │  Ubuntu 22.04 + XFCE Desktop                  │  │  │  │
    │  │  │  │  ├── Xvfb (display virtual :99)               │  │  │  │
    │  │  │  │  ├── x11vnc + websockify + noVNC              │  │  │  │
    │  │  │  │  ├── Nginx (SSL termination + auth)           │  │  │  │
    │  │  │  │  ├── Google Chrome + Playwright               │  │  │  │
    │  │  │  │  ├── Python 3.11 + Poetry + Django            │  │  │  │
    │  │  │  │  └── Systemd timers (23:00 & 12:00 EST)       │  │  │  │
    │  │  │  └───────────────────────────────────────────────┘  │  │  │
    │  │  │                                                     │  │  │
    │  │  │  Puertos: 22(SSH), 443(noVNC+HTTPS)                │  │  │
    │  │  └─────────────────────────────────────────────────────┘  │  │
    │  └──────────────────────────────────────────────────────────┘  │
    │                              │                                  │
    │                              ▼ (Private)                        │
    │  ┌──────────────────────────────────────────────────────────┐  │
    │  │  EC2 Databases (existente)                                │  │
    │  │  ├── PostgreSQL:5432                                      │  │
    │  │  └── MongoDB:27017                                        │  │
    │  └──────────────────────────────────────────────────────────┘  │
    │                                                                 │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
    │  │     ECR     │  │     SSM     │  │     SNS + Lambda        │ │
    │  │  (imágenes) │  │  (secretos) │  │  (notificaciones)       │ │
    │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
    └────────────────────────────────────────────────────────────────┘
```

---

## Flujo CI/CD

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Push a branch  │────▶│   CodeBuild     │────▶│  EC2 Refresh    │
│  (qa/prod)      │     │  Build + Push   │     │  Pull + Restart │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      │                       │
         │              ┌───────▼───────┐               │
         │              │     ECR       │               │
         │              │  Docker Image │               │
         │              └───────────────┘               │
         │                                              │
         └──────────────── Webhook ─────────────────────┘
```

---

## Flujo de Ejecución Programada

```
┌─────────────────────────────────────────────────────────────────┐
│                    Systemd Timer                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  scraper-scheduler.timer                                 │    │
│  │  ├── 23:00 EST (04:00 UTC)                              │    │
│  │  └── 12:00 EST (17:00 UTC)                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  scraper.service                                         │    │
│  │  1. Inicia display virtual (Xvfb :99)                   │    │
│  │  2. Ejecuta python main.py                              │    │
│  │  3. Chrome abre en display :99 (visible via noVNC)      │    │
│  │  4. Procesa todos los ScraperJobs disponibles           │    │
│  │  5. Logs → CloudWatch + archivo local                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    ▼                   ▼                        │
│              ┌──────────┐        ┌──────────┐                   │
│              │ SUCCESS  │        │  ERROR   │                   │
│              └──────────┘        └────┬─────┘                   │
│                                       │                         │
│                                       ▼                         │
│                    ┌─────────────────────────────────┐          │
│                    │  SNS → Lambda                    │          │
│                    │  ├── Email (SES)                │          │
│                    │  ├── Slack webhook              │          │
│                    │  └── Teams webhook              │          │
│                    └─────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estructura de Archivos

```
expertel_webscrapers/
├── deployment/
│   ├── PLAN.md                          # Este archivo
│   ├── README.md                        # Documentación de uso
│   │
│   ├── aws/
│   │   ├── README.md
│   │   ├── manage-secrets.sh            # Gestión de secretos SSM
│   │   ├── validate-secrets.sh          # Validación pre-deploy
│   │   ├── plan-dev.sh
│   │   ├── plan-qa.sh
│   │   ├── plan-prod.sh
│   │   ├── deploy-dev.sh
│   │   ├── deploy-qa.sh
│   │   ├── deploy-prod.sh
│   │   │
│   │   └── terraform/
│   │       ├── environments/
│   │       │   ├── dev/
│   │       │   │   ├── 00-versions.tf
│   │       │   │   ├── 01-backend.tf
│   │       │   │   ├── 02-locals.tf
│   │       │   │   ├── 03-variables.tf
│   │       │   │   ├── 04-data.tf        # Referencia VPC/subnets del backend
│   │       │   │   ├── 10-security.tf    # Security groups
│   │       │   │   ├── 20-compute.tf     # EC2 scraper
│   │       │   │   ├── 30-ssm.tf         # Parámetros config
│   │       │   │   ├── 40-notifications.tf # SNS + Lambda
│   │       │   │   ├── 50-codebuild.tf   # CI/CD
│   │       │   │   └── 90-outputs.tf
│   │       │   ├── qa/
│   │       │   │   └── (misma estructura)
│   │       │   └── prod/
│   │       │       └── (misma estructura)
│   │       │
│   │       └── modules/
│   │           ├── scraper-instance/
│   │           │   ├── main.tf
│   │           │   ├── variables.tf
│   │           │   ├── outputs.tf
│   │           │   └── templates/
│   │           │       ├── user_data.sh
│   │           │       ├── scraper.service
│   │           │       ├── scraper-scheduler.timer
│   │           │       └── novnc-nginx.conf
│   │           │
│   │           ├── notifications/
│   │           │   ├── main.tf
│   │           │   ├── variables.tf
│   │           │   ├── outputs.tf
│   │           │   └── lambda/
│   │           │       └── notify.py
│   │           │
│   │           └── codebuild/
│   │               ├── main.tf
│   │               ├── variables.tf
│   │               └── outputs.tf
│   │
│   ├── docker/
│   │   ├── Dockerfile                   # Para desarrollo local
│   │   ├── Dockerfile.production        # Para EC2
│   │   └── docker-compose.yml
│   │
│   └── windows/
│       ├── Manage-Secrets.ps1
│       ├── Plan-Environment.ps1
│       └── Deploy-Environment.ps1
│
└── buildspec.yml                        # CodeBuild build spec (raíz del proyecto)
```

---

## Variables SSM Parameter Store

### Secretos (SecureString) - Configurados manualmente via manage-secrets.sh

| Path | Descripción |
|------|-------------|
| `/experteliq2-scraper/{env}/database/password` | Password PostgreSQL |
| `/experteliq2-scraper/{env}/backend-api/key` | API Key del backend |
| `/experteliq2-scraper/{env}/cryptography/key` | Clave de encriptación |
| `/experteliq2-scraper/{env}/azure/client-secret` | Azure AD client secret |
| `/experteliq2-scraper/{env}/anthropic/api-key` | Anthropic API key |
| `/experteliq2-scraper/{env}/novnc/password` | Password acceso noVNC |
| `/experteliq2-scraper/{env}/slack/webhook-url` | Slack webhook URL |
| `/experteliq2-scraper/{env}/teams/webhook-url` | Teams webhook URL |

### Configuración (String) - Generados automáticamente por Terraform

| Path | Descripción | Origen |
|------|-------------|--------|
| `/experteliq2-scraper/{env}/database/host` | Host PostgreSQL | Output de backend databases |
| `/experteliq2-scraper/{env}/database/name` | Nombre BD | Variable |
| `/experteliq2-scraper/{env}/database/port` | Puerto (5432) | Constante |
| `/experteliq2-scraper/{env}/database/username` | Usuario BD | Variable |
| `/experteliq2-scraper/{env}/backend-api/url` | URL del backend | Output de backend ALB |
| `/experteliq2-scraper/{env}/azure/client-id` | Azure client ID | Variable |
| `/experteliq2-scraper/{env}/azure/tenant-id` | Azure tenant ID | Variable |
| `/experteliq2-scraper/{env}/azure/user-email` | Email notificaciones | Variable |
| `/experteliq2-scraper/{env}/mfa-service/url` | URL servicio MFA | Variable |
| `/experteliq2-scraper/{env}/config/novnc-url` | URL acceso noVNC | Output |

---

## Notificaciones

### Canales configurados

| Canal | Método | Cuándo |
|-------|--------|--------|
| **Email** | AWS SES | Errores críticos, resumen diario |
| **Slack** | Webhook | Errores, inicio/fin de ejecución |
| **Teams** | Webhook | Errores, inicio/fin de ejecución |

### Eventos notificados

| Evento | Email | Slack | Teams |
|--------|-------|-------|-------|
| Inicio ejecución programada | ❌ | ✅ | ✅ |
| Fin exitoso | ❌ | ✅ | ✅ |
| Error en scraper individual | ❌ | ✅ | ✅ |
| Error crítico (servicio caído) | ✅ | ✅ | ✅ |
| Resumen diario | ✅ | ❌ | ❌ |

---

## Costos Estimados (mensual)

| Recurso | Especificación | Costo |
|---------|---------------|-------|
| EC2 t3.medium | 2 vCPU, 4GB RAM, 24/7 | ~$30 |
| EBS gp3 | 50GB root + 20GB data | ~$8 |
| Data transfer | ~50GB/mes estimado | ~$5 |
| CloudWatch Logs | 10GB/mes | ~$5 |
| SSM Parameters | <100 parámetros | Free |
| SNS + Lambda | <1000 invocaciones | Free tier |
| CodeBuild | ~100 builds/mes | ~$5 |
| **Total** | | **~$53/mes** |

---

## Acceso noVNC

### URL de acceso
```
https://scraper-{env}.expertel.com/vnc/
```

### Autenticación
- Nginx Basic Auth (usuario + password)
- Password almacenado en SSM Parameter Store
- HTTPS obligatorio (certificado Let's Encrypt o ACM)

### Resolución recomendada
- 1920x1080 (configurable)
- Escala automática en browser

---

## Pasos de Deployment

### 1. Setup inicial (una vez por ambiente)

```bash
# 1.1 Crear bucket S3 para Terraform state
aws s3 mb s3://experteliq2-scraper-terraform-state-{env} --region us-east-2

# 1.2 Configurar secretos
./deployment/aws/manage-secrets.sh setup {env}

# 1.3 Validar secretos
./deployment/aws/validate-secrets.sh all {env}
```

### 2. Deployment de infraestructura

```bash
# 2.1 Planificar cambios
./deployment/aws/plan-{env}.sh

# 2.2 Aplicar cambios
./deployment/aws/deploy-{env}.sh
```

### 3. Verificación

```bash
# 3.1 Obtener URL de noVNC
cd deployment/aws/terraform/environments/{env}
terraform output novnc_url

# 3.2 Verificar acceso
curl -I https://scraper-{env}.expertel.com/vnc/

# 3.3 Verificar ejecución programada
ssh scraper-{env} "systemctl status scraper-scheduler.timer"
```

---

## Próximos pasos

1. ✅ Plan aprobado
2. ⏳ Crear estructura de carpetas
3. ⏳ Implementar módulo Terraform scraper-instance
4. ⏳ Implementar módulo de notificaciones
5. ⏳ Implementar CodeBuild CI/CD
6. ⏳ Crear scripts de gestión de secretos
7. ⏳ Crear buildspec.yml
8. ⏳ Documentación completa
9. ⏳ Testing en ambiente dev
10. ⏳ Deploy a QA

---

**¿Aprobado para proceder con la implementación?**
