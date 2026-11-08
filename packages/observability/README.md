# Observabilidade TypeScript

Logger compartilhado pelo app mobile/web e pelo cliente Firebase. Fornece eventos
JSON no console, catálogo de campos permitidos, níveis configuráveis, identificação
aleatória de sessão/operação e classificação de erros sem mensagens brutas.

```ts
import { configureLogging, log, reportError } from '@hinario/observability';

configureLogging({ environment: 'production', level: 'info' });
log('app.init.started');
reportError('app.init.failed', new Error('Esta mensagem não será registrada'));
```

Use eventos do catálogo em `src/index.ts`; ao adicionar um evento, defina o nível,
os campos permitidos e os validadores dos valores. Não passe objetos de domínio ou
mensagens de exceções como contexto. `reportError` evita registrar o mesmo objeto
de exceção mais de uma vez. Falhas no destino de logs não interrompem a aplicação.

Execute `corepack pnpm logs:test` na raiz para validar o logger.
As convenções e configurações estão no [guia de logs](../../infra/observability/README.md).
