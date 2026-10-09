# ADR-030: manutenção e disponibilidade programada da frota

Status: proposta para revisão na OC100 / Issue #147

## Contexto

`CONFIRMADO`: OC64/ADR-023 reserva veículos por carregamento/viagem; OC105
arquiva cadastros com active. Issue #147 autoriza manutenção preventiva e
corretiva, períodos de indisponibilidade, quilometragem opcional e revisão por
data/km. Sem telemetria, estoque de peças, contas a pagar ou gestão de oficina.

## Decisão implementada

`CONFIRMADO`: TruckMaintenance pertence ao módulo trucks. Registros são
imutáveis após criação, exceto encerramento e revisão associada, sem DELETE.
Início/fim programado usam UTC; fim opcional, exclusivo, maior que início.
Manutenção aberta bloqueia novas operações durante [starts_at, ends_at);
sem fim bloqueia indefinidamente. Encerrar remove apenas esse bloqueio.
Encerrar uma janela futura cancela a indisponibilidade, preservando o registro.
Janelas sobrepostas são permitidas: encerrar uma não libera outra.

`CONFIRMADO`: períodos futuros não bloqueiam operações atuais; após o início,
novos cálculos/recálculos, aprovação, distribuição, criação/início de
carregamento e criação/início de viagem validam manutenção no backend. Operações
já em andamento podem concluir; manutenção não cancela histórico nem active.
Revisão vencida é alerta independente, sem inventar bloqueio automático.

`CONFIRMADO`: a linha do caminhão é bloqueada antes de manutenção, odômetro e
reserva operacional. Criar manutenção (inclusive futura) com operação ativa
retorna TRUCK_OPERATION_CONFLICT: não há previsão confiável de liberação para
prometer uma janela. Operações iniciadas antes de uma janela futura podem
concluir após seu início, mas novos inícios são impedidos nesse período.
Não inferir duração de viagem nem introduzir roteirização para prever isso.

`CONFIRMADO`: serviços públicos de TruckService concentram o bloqueio temporal;
FleetAvailabilityService combina active, conflito operacional e manutenção,
expondo has_maintenance_conflict sem reaproveitar has_operation_conflict.
A disponibilidade é calculada na leitura. Não criar estado persistido de
"disponível", nem alterar a regra de reserva de planos da ADR-023.

`CONFIRMADO`: odometer_km é opcional e inteiro não negativo, nunca diminui quando
informado. Manutenção registra km inicial e final; encerramento pode programar
próxima revisão por UTC e/ou km. Data informada deve ser futura, km deve superar
o odômetro conhecido. Campos de revisão omitidos preservam programação;
null explícito limpa esse critério. O histórico guarda a programação resultante.
Custo opcional é Decimal/JSON numérico, sem módulo financeiro novo.

`CONFIRMADO`: ADMIN e LOGISTICS_MANAGER escrevem; CHECKER consulta histórico e
frota; DRIVER não acessa cadastro. Auditoria de criação, encerramento e atualização
de km fica na mesma transação. Falha faz rollback de todo o estado.

`CONFIRMADO`: migration 20261009_0018 segue 20261008_0017, sem inventar km ou
histórico para dados existentes; downgrade sem dados OC100 preserva OC99/OC105.
Downgrade com manutenção, revisão, km ou auditoria OC100 é bloqueado para impedir
perda silenciosa, seguindo a proteção das migrations anteriores.

## Consequências

`CONFIRMADO`: histórico e vencimentos são consultáveis no cadastro; a frota
explica manutenção e o planejamento omite veículos com bloqueio temporal atual.
A API é aditiva. Dados e fluxos de endereços/arquivamento permanecem intactos.

`RISCO IDENTIFICADO`: não há horizonte de duração confiável das operações.
A janela bloqueia novas operações no período, mas não aborta viagens existentes.
SQL externo deve respeitar monotonicidade de odômetro e locks, além das
constraints de domínio. Eventual reversão após uso requer preservar histórico.
