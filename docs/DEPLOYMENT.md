# Guía de Despliegue - Sistema de Alertas de Precio Keepa IA

Esta guía te ayudará a desplegar el sistema de alertas de precio en producción, incluyendo la configuración de cron para verificación automática y el setup de email.

## 📋 Requisitos Previos

- Servidor con Python 3.8+
- Base de datos MySQL/PostgreSQL
- Servidor web (Nginx + Gunicorn recomendado)
- Acceso SSH al servidor
- Dominio configurado (opcional)

## 🚀 Pasos de Despliegue

### 1. Preparación del Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias del sistema
sudo apt install python3-pip python3-venv nginx mysql-server git -y

# Crear usuario para la aplicación
sudo adduser keepa-app
sudo usermod -aG sudo keepa-app
```

### 2. Configuración del Proyecto

```bash
# Cambiar al usuario de la aplicación
sudo su - keepa-app

# Clonar el repositorio
git clone <tu-repositorio> /home/keepa-app/keepa_ia
cd /home/keepa-app/keepa_ia

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno

```bash
# Crear archivo .env
cp env.example .env
nano .env
```

**Configuración mínima para .env:**

```env
# Django Settings
SECRET_KEY=tu-secret-key-super-seguro-aqui
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com,tu-ip-servidor

# Database Settings
DB_ENGINE=django.db.backends.mysql
DB_NAME=keepa_ia_prod
DB_USER=keepa_user
DB_PASSWORD=tu-password-seguro
DB_HOST=localhost
DB_PORT=3306

# Keepa API
KEEPA_API_KEY=tu-keepa-api-key

# Email Settings (Producción)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=noreply@tu-dominio.com
SERVER_EMAIL=admin@tu-dominio.com

# Site Settings
SITE_NAME=Keepa IA
SITE_URL=https://tu-dominio.com
```

### 4. Configuración de Base de Datos

```bash
# Conectar a MySQL
sudo mysql -u root -p

# Crear base de datos y usuario
CREATE DATABASE keepa_ia_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'keepa_user'@'localhost' IDENTIFIED BY 'tu-password-seguro';
GRANT ALL PRIVILEGES ON keepa_ia_prod.* TO 'keepa_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Migraciones y Configuración Inicial

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recopilar archivos estáticos
python manage.py collectstatic --noinput
```

### 6. Configuración de Gunicorn

```bash
# Crear archivo de configuración de Gunicorn
nano /home/keepa-app/keepa_ia/gunicorn.conf.py
```

**Contenido de gunicorn.conf.py:**

```python
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
```

```bash
# Crear servicio systemd para Gunicorn
sudo nano /etc/systemd/system/keepa-ia.service
```

**Contenido del servicio:**

```ini
[Unit]
Description=Keepa IA Django Application
After=network.target

[Service]
User=keepa-app
Group=www-data
WorkingDirectory=/home/keepa-app/keepa_ia
Environment="PATH=/home/keepa-app/keepa_ia/venv/bin"
ExecStart=/home/keepa-app/keepa_ia/venv/bin/gunicorn --config gunicorn.conf.py keepa_ia.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar el servicio
sudo systemctl daemon-reload
sudo systemctl enable keepa-ia
sudo systemctl start keepa-ia
sudo systemctl status keepa-ia
```

### 7. Configuración de Nginx

```bash
# Crear configuración de Nginx
sudo nano /etc/nginx/sites-available/keepa-ia
```

**Contenido de la configuración:**

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/keepa-app/keepa_ia;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root /home/keepa-app/keepa_ia;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Habilitar el sitio
sudo ln -s /etc/nginx/sites-available/keepa-ia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Configuración de SSL (Opcional pero Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado SSL
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

## ⏰ Configuración de Cron para Alertas de Precio

### Opción 1: Cron Básico (Recomendado para MVP)

```bash
# Editar crontab del usuario keepa-app
sudo crontab -e -u keepa-app
```

**Agregar las siguientes líneas:**

```bash
# Verificar alertas cada 6 horas (4 veces al día)
0 */6 * * * cd /home/keepa-app/keepa_ia && source venv/bin/activate && python manage.py check_price_alerts --frequency 4 >> /var/log/keepa-alerts.log 2>&1

# Verificar alertas cada 12 horas (2 veces al día)
0 */12 * * * cd /home/keepa-app/keepa_ia && source venv/bin/activate && python manage.py check_price_alerts --frequency 2 >> /var/log/keepa-alerts.log 2>&1

# Verificar alertas una vez al día
0 9 * * * cd /home/keepa-app/keepa_ia && source venv/bin/activate && python manage.py check_price_alerts --frequency 1 >> /var/log/keepa-alerts.log 2>&1

# Limpiar logs antiguos (mantener solo últimos 30 días)
0 2 * * * find /var/log/keepa-alerts.log -mtime +30 -delete
```

### Opción 2: Cron Avanzado con Logging

```bash
# Crear script de verificación
sudo nano /home/keepa-app/check_alerts.sh
```

**Contenido del script:**

```bash
#!/bin/bash

# Configuración
PROJECT_DIR="/home/keepa-app/keepa_ia"
LOG_FILE="/var/log/keepa-alerts.log"
VENV_PATH="$PROJECT_DIR/venv/bin/activate"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_FILE
}

# Cambiar al directorio del proyecto
cd $PROJECT_DIR

# Activar entorno virtual
source $VENV_PATH

# Verificar alertas según frecuencia
FREQUENCY=$1
if [ -z "$FREQUENCY" ]; then
    FREQUENCY="all"
fi

log "Iniciando verificación de alertas (frecuencia: $FREQUENCY)"

# Ejecutar comando de verificación
if [ "$FREQUENCY" = "all" ]; then
    python manage.py check_price_alerts
else
    python manage.py check_price_alerts --frequency $FREQUENCY
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "Verificación completada exitosamente"
else
    log "Error en verificación (código: $EXIT_CODE)"
fi

log "---"
```

```bash
# Hacer ejecutable
sudo chmod +x /home/keepa-app/check_alerts.sh

# Configurar cron
sudo crontab -e -u keepa-app
```

**Cron con script:**

```bash
# Verificar alertas cada 6 horas
0 */6 * * * /home/keepa-app/check_alerts.sh 4

# Verificar alertas cada 12 horas  
0 */12 * * * /home/keepa-app/check_alerts.sh 2

# Verificar alertas diariamente
0 9 * * * /home/keepa-app/check_alerts.sh 1

# Verificación completa semanal (domingos a las 2 AM)
0 2 * * 0 /home/keepa-app/check_alerts.sh all
```

## 📧 Configuración de Email

### Gmail SMTP (Recomendado para empezar)

1. **Habilitar autenticación de 2 factores** en tu cuenta de Gmail
2. **Generar contraseña de aplicación:**
   - Ve a Configuración de Google > Seguridad
   - Busca "Contraseñas de aplicaciones"
   - Genera una nueva para "Mail"
   - Usa esta contraseña en `EMAIL_HOST_PASSWORD`

### SendGrid (Recomendado para producción)

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=tu-sendgrid-api-key
```

### AWS SES (Para alto volumen)

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-ses-smtp-username
EMAIL_HOST_PASSWORD=tu-ses-smtp-password
```

## 🔧 Comandos de Mantenimiento

### Verificar Estado del Sistema

```bash
# Estado de servicios
sudo systemctl status keepa-ia
sudo systemctl status nginx

# Ver logs de la aplicación
sudo journalctl -u keepa-ia -f

# Ver logs de alertas
sudo tail -f /var/log/keepa-alerts.log

# Verificar cron jobs
sudo crontab -l -u keepa-app
```

### Comandos de Django Útiles

```bash
# Activar entorno virtual
source /home/keepa-app/keepa_ia/venv/bin/activate

# Verificar alertas manualmente
python manage.py check_price_alerts --dry-run

# Verificar alertas con frecuencia específica
python manage.py check_price_alerts --frequency 2

# Forzar actualización de precios
python manage.py check_price_alerts --force-update

# Crear superusuario
python manage.py createsuperuser

# Recopilar archivos estáticos
python manage.py collectstatic --noinput

# Ejecutar migraciones
python manage.py migrate
```

### Backup de Base de Datos

```bash
# Crear backup
mysqldump -u keepa_user -p keepa_ia_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
mysql -u keepa_user -p keepa_ia_prod < backup_20240101_120000.sql
```

## 🚨 Troubleshooting

### Problemas Comunes

1. **Alertas no se ejecutan:**
   ```bash
   # Verificar logs de cron
   sudo tail -f /var/log/syslog | grep CRON
   
   # Verificar permisos
   sudo chown -R keepa-app:keepa-app /home/keepa-app/keepa_ia
   ```

2. **Emails no se envían:**
   ```bash
   # Probar configuración de email
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
   ```

3. **Error de Keepa API:**
   ```bash
   # Verificar API key
   python manage.py shell
   >>> from products.keepa_service import KeepaService
   >>> service = KeepaService()
   ```

4. **Problemas de permisos:**
   ```bash
   # Corregir permisos
   sudo chown -R keepa-app:www-data /home/keepa-app/keepa_ia
   sudo chmod -R 755 /home/keepa-app/keepa_ia
   ```

### Monitoreo

```bash
# Crear script de monitoreo
sudo nano /home/keepa-app/monitor.sh
```

**Contenido del script de monitoreo:**

```bash
#!/bin/bash

# Verificar servicios
if ! systemctl is-active --quiet keepa-ia; then
    echo "ALERT: Keepa IA service is down!" | mail -s "Service Alert" admin@tu-dominio.com
fi

if ! systemctl is-active --quiet nginx; then
    echo "ALERT: Nginx service is down!" | mail -s "Service Alert" admin@tu-dominio.com
fi

# Verificar espacio en disco
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "ALERT: Disk usage is ${DISK_USAGE}%" | mail -s "Disk Alert" admin@tu-dominio.com
fi

# Verificar logs de errores
if grep -q "ERROR" /var/log/keepa-alerts.log; then
    echo "ALERT: Errors found in alert logs" | mail -s "Error Alert" admin@tu-dominio.com
fi
```

```bash
# Hacer ejecutable y agregar a cron
sudo chmod +x /home/keepa-app/monitor.sh
sudo crontab -e -u root
# Agregar: 0 */6 * * * /home/keepa-app/monitor.sh
```

## 📊 Optimizaciones de Rendimiento

### Para Alto Volumen de Alertas

1. **Usar Celery en lugar de cron:**
   ```bash
   pip install celery redis
   ```

2. **Configurar Redis:**
   ```bash
   sudo apt install redis-server
   sudo systemctl enable redis-server
   ```

3. **Optimizar base de datos:**
   ```sql
   -- Índices para mejorar rendimiento
   CREATE INDEX idx_price_alert_user_active ON products_pricealert(user_id, is_active);
   CREATE INDEX idx_price_alert_frequency ON products_pricealert(frequency, last_checked);
   CREATE INDEX idx_notification_user_read ON products_notification(user_id, is_read);
   ```

## 🔒 Consideraciones de Seguridad

1. **Firewall:**
   ```bash
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

2. **Fail2ban:**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

3. **Backup automático:**
   ```bash
   # Agregar a cron
   0 2 * * * mysqldump -u keepa_user -p keepa_ia_prod | gzip > /backups/keepa_$(date +\%Y\%m\%d).sql.gz
   ```

## 📈 Escalabilidad

Para sistemas con muchos usuarios:

1. **Load Balancer** (Nginx + múltiples instancias Gunicorn)
2. **Base de datos separada** (RDS/Aurora)
3. **Cache** (Redis)
4. **CDN** para archivos estáticos
5. **Queue system** (Celery + Redis/RabbitMQ)

---

## ✅ Checklist de Despliegue

- [ ] Servidor configurado y actualizado
- [ ] Base de datos creada y configurada
- [ ] Variables de entorno configuradas
- [ ] Migraciones ejecutadas
- [ ] Superusuario creado
- [ ] Gunicorn configurado y funcionando
- [ ] Nginx configurado y funcionando
- [ ] SSL configurado (opcional)
- [ ] Cron jobs configurados
- [ ] Email configurado y probado
- [ ] Monitoreo configurado
- [ ] Backup configurado
- [ ] Firewall configurado
- [ ] Pruebas de alertas realizadas

¡Tu sistema de alertas de precio está listo para producción! 🎉
