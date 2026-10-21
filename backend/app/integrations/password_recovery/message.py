"""Render a branded recovery email locally, with a plain-text alternative."""

from email.message import EmailMessage
from email.utils import formataddr
from html import escape


def build_recovery_message(
    recipient: str, token: str, sender: str, recovery_url: str
) -> EmailMessage:
    """Include the reset token only in links, never in headers or remote assets."""
    link = f"{recovery_url}#token={token}"
    safe_link = escape(link, quote=True)

    message = EmailMessage()
    message["Subject"] = "LoadX | Redefinição de senha"
    message["From"] = formataddr(("LoadX | Segurança", sender), charset="utf-8")
    message["To"] = recipient
    message.set_content(
        "Olá!\n\n"
        "Recebemos uma solicitação para redefinir a senha da sua conta no LoadX.\n\n"
        "Para criar uma nova senha, acesse este link:\n"
        f"{link}\n\n"
        "O link expira em 15 minutos e só pode ser utilizado uma vez.\n\n"
        "Se não solicitou a recuperação, ignore esta mensagem. "
        "Sua senha permanecerá a mesma.\n\n"
        "O LoadX nunca solicita senhas ou códigos do autenticador por e-mail.\n\n"
        "LoadX | Smart Logistics\n"
        "Mensagem automática de segurança.\n"
    )

    html = f"""\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Redefinição de senha | LoadX</title>
</head>
<body style="margin:0;padding:0;background:#eef1f5;
             font-family:Arial,Helvetica,sans-serif;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;
            max-width:0;opacity:0;overflow:hidden;">
  Redefina sua senha do LoadX. Link válido por 15 minutos.
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#eef1f5;">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:560px;background:#fff;border:1px solid #e1e6ec;
              border-radius:12px;">
<tr><td style="padding:30px 32px;background:#151b24;">
  <span style="font-size:29px;font-weight:800;letter-spacing:-1px;
               color:#fff;">Load<span style="color:#e6a145;">X</span></span>
  <div style="font-size:11px;letter-spacing:1.6px;color:#c4cfdd;
              margin-top:8px;font-weight:700;">SEGURANÇA DA CONTA</div>
</td></tr>
<tr><td style="padding:36px 32px;color:#424c5b;">
<h1 style="font-size:25px;line-height:1.25;color:#18212d;
           margin:0 0 24px;">Recupere seu acesso ao LoadX</h1>
<p style="font-size:15px;line-height:1.7;margin:0 0 16px;">Olá!</p>
<p style="font-size:15px;line-height:1.7;margin:0 0 25px;">
  Recebemos uma solicitação para redefinir a senha da sua conta no LoadX.
</p>
<table role="presentation" cellpadding="0" cellspacing="0">
<tr><td align="center" bgcolor="#e6a145"
        style="background:#e6a145;border-radius:9px;">
  <a href="{safe_link}"
     style="display:inline-block;padding:15px 28px;color:#18212d;
            text-decoration:none;font-weight:700;font-size:15px;
            border-radius:9px;">Redefinir minha senha</a>
</td></tr>
</table>
<p style="font-size:14px;line-height:1.7;margin:24px 0 12px;">
  <strong>O link expira em 15 minutos</strong> e pode ser utilizado uma vez.
</p>
<p style="font-size:12px;line-height:1.6;margin:0 0 8px;color:#697584;">
  Se o botão não funcionar, copie o endereço abaixo no navegador:
</p>
<p style="font-size:12px;line-height:1.6;word-break:break-all;
          overflow-wrap:anywhere;margin:0 0 25px;">
  <a href="{safe_link}" style="color:#936017;">{safe_link}</a>
</p>
<div style="padding-top:22px;border-top:1px solid #e5e9ef;">
<p style="font-size:14px;line-height:1.7;margin:0 0 12px;">
  <strong>Não solicitou essa alteração?</strong>
  Ignore esta mensagem. Sua senha permanecerá a mesma.
</p>
<p style="font-size:12px;line-height:1.7;margin:0;color:#697584;">
  O LoadX nunca solicita senhas ou códigos do autenticador por e-mail.
</p>
</div>
</td></tr>
<tr><td align="center" style="background:#f7f9fb;
                            border-top:1px solid #e5e9ef;padding:24px;">
<p style="font-size:12px;font-weight:700;color:#34404e;
          margin:0 0 6px;">LoadX | Smart Logistics</p>
<p style="font-size:11px;color:#758092;margin:0;">
  Mensagem automática de segurança.
</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
    message.add_alternative(html, subtype="html")
    return message
