# Bitácora del proyecto integrador

## Entrada 1, semana 12 (13-11-2026)

**Integrantes:** Diego Jaune y Sebastián Asencio. Asistencia presencial: por confirmar por el equipo.

**Decisiones y motivos:** continuar mensajería; Directorio como entrada y Conversacion
como borrador remoto. Usar single para compartir la entrada y objetos explícitos
para cada conversación; session se probó, pero liga el estado a la conexión.
Conservar dominio.py de S11, incluido el contador inicial heredado, para comparar transportes.

**Trabajo realizado:** adaptación Pyro5, CLI, pruebas de referencia/copia, cancelación,
excepciones, modos de instancia y fallas. Observaciones y calidad en semana-12/laboratorio/.
Propuesta del integrador: separar Buzon y distribuir entregas entre dos workers.

**Problemas y decisiones:** las referencias no sobreviven al reinicio y los datos
actuales son volátiles. El integrador agregará persistencia y deduplicación; no se
reintentan escrituras automáticamente en S12. Los borradores abandonados necesitan TTL.

| Próximo paso | Responsable propuesto, a validar por el equipo | Plazo |
|---|---|---|
| Revisar alcance con docente y registrar decisión real | Ambos | Revisión docente |
| Integrar RabbitMQ con dos workers y ACK manual | Diego Jaune | 26-11-2026, 18:00 |
| Separar Buzon, persistencia y deduplicación | Sebastián Asencio | 26-11-2026, 18:00 |
| Crear diagrama draw.io y actualizar README | Ambos | Hito S13 |
| Implementar y probar coordinación distribuida | Ambos | 11-12-2026 |

Pendientes administrativos: aprobación docente, validación de responsables y publicación
de la entrega en el repositorio remoto. Esta entrada no certifica asistencia ni aprobación.

