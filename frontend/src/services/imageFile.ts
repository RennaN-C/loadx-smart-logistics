/** Limite do backend para imagem enviada: 5 MiB antes e depois da normalização. */
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

const ACCEPTED = new Set(["image/png", "image/jpeg"]);

/** Valor do `accept` dos campos de arquivo que aceitam estas imagens. */
export const IMAGE_ACCEPT = "image/png,image/jpeg";

/**
 * Lê uma imagem escolhida pelo usuário e devolve só o base64, sem o prefixo
 * `data:`.
 *
 * As regras conferidas aqui são as MESMAS do backend (PNG/JPEG, 5 MiB) e não o
 * substituem: ele revalida pelos bytes, não pelo que o navegador declarou como
 * tipo. A checagem local existe para a pessoa não esperar o envio de um arquivo
 * de 40 MB só para receber recusa — e o limite de 20 milhões de pixels fica
 * deliberadamente de fora, porque só se conhece decodificando a imagem.
 *
 * Compartilhado porque anexos operacionais (OC110) e evidências de entrega
 * (OC80/OC81) seguem o mesmo contrato de upload. Duas cópias divergiriam na
 * primeira vez que o limite mudar.
 */
export function readImageAsBase64(file: File): Promise<string> {
  if (!ACCEPTED.has(file.type) || file.size === 0 || file.size > MAX_IMAGE_BYTES) {
    // Texto preservado do módulo de anexos: deduplicar não é motivo para
    // mudar mensagem que o usuário já conhece.
    return Promise.reject(new Error("Selecione PNG/JPEG de até 5 MiB."));
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Não foi possível ler o arquivo."));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string" || !result.includes(",")) {
        reject(new Error("Arquivo inválido."));
        return;
      }
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.readAsDataURL(file);
  });
}
