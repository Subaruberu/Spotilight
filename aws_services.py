"""
aws_services.py — Módulo de integração AWS para SpotlightIA
Serviços: S3 (arquivos), Bedrock (IA), SES (e-mail), Lambda (automações)
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Configuração ──────────────────────────────────────────────────────────────
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET      = os.environ.get("S3_BUCKET", "spotlightia-docs")
USE_BEDROCK    = os.environ.get("USE_BEDROCK", "false").lower() == "true"
SES_SENDER     = os.environ.get("SES_SENDER", "")
LAMBDA_ARN     = os.environ.get("LAMBDA_REMINDER_ARN", "")

# Tenta importar boto3 (SDK da AWS)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    AWS_DISPONIVEL = True
except ImportError:
    AWS_DISPONIVEL = False
    logger.warning("boto3 não instalado. Funcionalidades AWS desabilitadas.")


def get_client(service: str):
    """Retorna um cliente boto3 para o serviço especificado."""
    if not AWS_DISPONIVEL:
        return None
    try:
        return boto3.client(service, region_name=AWS_REGION)
    except NoCredentialsError:
        logger.error(f"Credenciais AWS não configuradas para {service}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# S3 — ARMAZENAMENTO DE ARQUIVOS
# ═══════════════════════════════════════════════════════════════════════════════

def s3_upload(file_bytes: bytes, filename: str, tenant_id: str, evento: str = "") -> dict:
    """Faz upload de arquivo para S3, organizado por tenant/evento."""
    s3 = get_client("s3")
    if not s3:
        return {"ok": False, "erro": "AWS S3 não disponível"}

    key = f"{tenant_id}/{evento}/{filename}" if evento else f"{tenant_id}/{filename}"
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=file_bytes,
            ContentType=_guess_mime(filename),
            Metadata={
                "tenant": tenant_id,
                "evento": evento,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        )
        url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
        return {"ok": True, "url": url, "key": key}
    except ClientError as e:
        return {"ok": False, "erro": str(e)}


def s3_download(key: str) -> dict:
    """Baixa arquivo do S3."""
    s3 = get_client("s3")
    if not s3:
        return {"ok": False, "erro": "AWS S3 não disponível"}
    try:
        resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return {"ok": True, "body": resp["Body"].read(), "content_type": resp["ContentType"]}
    except ClientError as e:
        return {"ok": False, "erro": str(e)}


def s3_list(tenant_id: str, evento: str = "") -> list:
    """Lista arquivos do tenant no S3."""
    s3 = get_client("s3")
    if not s3:
        return []
    prefix = f"{tenant_id}/{evento}/" if evento else f"{tenant_id}/"
    try:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        return [
            {"key": obj["Key"], "size": obj["Size"], "modified": obj["LastModified"].isoformat()}
            for obj in resp.get("Contents", [])
        ]
    except ClientError:
        return []


def s3_delete(key: str) -> bool:
    """Deleta arquivo do S3."""
    s3 = get_client("s3")
    if not s3:
        return False
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False


def s3_presigned_url(key: str, expira: int = 3600) -> str:
    """Gera URL temporária para download seguro (expira em 1h por padrão)."""
    s3 = get_client("s3")
    if not s3:
        return ""
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expira,
        )
    except ClientError:
        return ""


def _guess_mime(filename: str) -> str:
    """Adivinha o content-type pelo nome do arquivo."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mimes = {
        "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "txt": "text/plain", "csv": "text/csv", "json": "application/json",
        "html": "text/html", "svg": "image/svg+xml",
    }
    return mimes.get(ext, "application/octet-stream")


# ═══════════════════════════════════════════════════════════════════════════════
# AMAZON BEDROCK — IA (Claude, Llama, Titan)
# ═══════════════════════════════════════════════════════════════════════════════

def bedrock_chat(prompt: str, system: str = "", model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0", max_tokens: int = 1024) -> str:
    """Chama um modelo de IA via Amazon Bedrock."""
    if not USE_BEDROCK:
        return ""

    bedrock = get_client("bedrock-runtime")
    if not bedrock:
        return "AWS Bedrock não disponível"

    try:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        response = bedrock.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    except ClientError as e:
        return f"Erro Bedrock: {e}"
    except Exception as e:
        return f"Erro: {e}"


def bedrock_list_models() -> list:
    """Lista modelos disponíveis no Bedrock."""
    bedrock = get_client("bedrock")
    if not bedrock:
        return []
    try:
        resp = bedrock.list_foundation_models()
        return [
            {"id": m["modelId"], "nome": m["modelName"], "provider": m["providerName"]}
            for m in resp.get("modelSummaries", [])
        ]
    except ClientError:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# AMAZON SES — ENVIO DE E-MAILS
# ═══════════════════════════════════════════════════════════════════════════════

def ses_send_email(to: str, subject: str, html_body: str, text_body: str = "") -> dict:
    """Envia e-mail via Amazon SES."""
    ses = get_client("ses")
    if not ses or not SES_SENDER:
        return {"ok": False, "erro": "AWS SES não configurado"}

    try:
        body_config = {"Html": {"Charset": "UTF-8", "Data": html_body}}
        if text_body:
            body_config["Text"] = {"Charset": "UTF-8", "Data": text_body}

        resp = ses.send_email(
            Source=SES_SENDER,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Charset": "UTF-8", "Data": subject},
                "Body": body_config,
            },
        )
        return {"ok": True, "message_id": resp["MessageId"]}
    except ClientError as e:
        return {"ok": False, "erro": str(e)}


def ses_send_rsvp_confirmation(to: str, nome: str, evento: str, data: str, local: str) -> dict:
    """Envia e-mail de confirmação de RSVP via SES."""
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <div style="background:#6C63FF;padding:24px;text-align:center;border-radius:8px 8px 0 0">
      <h1 style="color:#fff;margin:0">SpotlightIA</h1>
    </div>
    <div style="padding:24px;border:1px solid #eee;border-top:none;border-radius:0 0 8px 8px">
      <h2>Presenca confirmada!</h2>
      <p>Ola, <strong>{nome}</strong>! Sua presenca no evento <strong>{evento}</strong> foi confirmada.</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr style="background:#f5f5f5"><td style="padding:8px">Data</td><td style="padding:8px"><strong>{data}</strong></td></tr>
        <tr><td style="padding:8px">Local</td><td style="padding:8px"><strong>{local}</strong></td></tr>
      </table>
      <p style="color:#888;font-size:12px">Spotlight Eventos</p>
    </div></body></html>"""
    return ses_send_email(to, f"Presenca confirmada — {evento}", html)


def ses_send_reminder(to: str, nome: str, evento: str, data: str, local: str) -> dict:
    """Envia lembrete de evento via SES."""
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <div style="background:#FFD93D;padding:20px;text-align:center;border-radius:8px 8px 0 0">
      <h2 style="color:#333;margin:0">Lembrete: {evento}</h2>
    </div>
    <div style="padding:24px;border:1px solid #eee;border-top:none;border-radius:0 0 8px 8px">
      <p>Ola, <strong>{nome}</strong>! Este e um lembrete do evento <strong>{evento}</strong>.</p>
      <p>Data: <strong>{data}</strong><br>Local: <strong>{local}</strong></p>
      <p>Nos vemos la!</p>
      <p style="color:#888;font-size:12px">Spotlight Eventos</p>
    </div></body></html>"""
    return ses_send_email(to, f"Lembrete: {evento} — {data}", html)


# ═══════════════════════════════════════════════════════════════════════════════
# AWS LAMBDA — AUTOMAÇÕES AGENDADAS
# ═══════════════════════════════════════════════════════════════════════════════

def lambda_schedule_reminder(evento: str, data_evento: str, emails: list, hours_before: int = 24) -> dict:
    """Agenda um lembrete via Lambda + EventBridge."""
    lmb = get_client("lambda")
    if not lmb or not LAMBDA_ARN:
        return {"ok": False, "erro": "AWS Lambda não configurado"}

    payload = {
        "action": "send_reminders",
        "evento": evento,
        "data_evento": data_evento,
        "emails": emails,
        "hours_before": hours_before,
    }
    try:
        resp = lmb.invoke(
            FunctionName=LAMBDA_ARN,
            InvocationType="Event",  # Assíncrono
            Payload=json.dumps(payload),
        )
        return {"ok": True, "status_code": resp["StatusCode"]}
    except ClientError as e:
        return {"ok": False, "erro": str(e)}


def lambda_generate_report(tenant_id: str, mes: str, ano: int) -> dict:
    """Aciona Lambda para gerar relatório mensal em PDF no S3."""
    lmb = get_client("lambda")
    if not lmb:
        return {"ok": False, "erro": "AWS Lambda não configurado"}

    payload = {
        "action": "generate_report",
        "tenant_id": tenant_id,
        "mes": mes,
        "ano": ano,
    }
    try:
        resp = lmb.invoke(
            FunctionName=os.environ.get("LAMBDA_REPORT_ARN", LAMBDA_ARN),
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        return {"ok": True, "status_code": resp["StatusCode"]}
    except ClientError as e:
        return {"ok": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# CLOUDWATCH — LOGS E MÉTRICAS
# ═══════════════════════════════════════════════════════════════════════════════

def cloudwatch_log(message: str, log_group: str = "/spotlightia/app"):
    """Envia log para CloudWatch."""
    cw = get_client("logs")
    if not cw:
        return
    try:
        cw.put_log_events(
            logGroupName=log_group,
            logStreamName=datetime.utcnow().strftime("%Y/%m/%d"),
            logEvents=[{
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "message": message,
            }],
        )
    except Exception:
        pass


def cloudwatch_metric(metric_name: str, value: float, unit: str = "Count"):
    """Publica métrica no CloudWatch."""
    cw = get_client("cloudwatch")
    if not cw:
        return
    try:
        cw.put_metric_data(
            Namespace="SpotlightIA",
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Timestamp": datetime.utcnow(),
            }],
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════════

def aws_status() -> dict:
    """Retorna status de cada serviço AWS."""
    status = {"disponivel": AWS_DISPONIVEL}
    if not AWS_DISPONIVEL:
        return status

    # S3
    try:
        s3 = get_client("s3")
        s3.head_bucket(Bucket=S3_BUCKET)
        status["s3"] = "ativo"
    except Exception:
        status["s3"] = "inativo"

    # Bedrock
    status["bedrock"] = "ativo" if USE_BEDROCK else "desabilitado"

    # SES
    status["ses"] = "ativo" if SES_SENDER else "nao_configurado"

    # Lambda
    status["lambda"] = "ativo" if LAMBDA_ARN else "nao_configurado"

    return status
