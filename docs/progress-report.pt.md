# Relatório de progresso do Visa Selfie

30 de setembro de 2026

A primeira fase do Visa Selfie está funcionando no ambiente de testes local. Já conseguimos percorrer o fluxo principal, desde a criação do cadastro de um solicitante até o recebimento e a análise do seu vídeo. A próxima etapa é disponibilizar essa mesma experiência online e testá-la em um notebook e em celulares reais.

Para os administradores, a aplicação oferece um espaço para cadastrar clientes, acompanhar o andamento de cada caso e identificar quem ainda precisa concluir o cadastro ou enviar uma gravação. Cada solicitante recebe um link privado de cadastro, que o administrador pode copiar e enviar pelo WhatsApp. Os links têm validade de 48 horas e podem ser substituídos quando necessário.

Para os solicitantes, o processo começa com o preenchimento dos dados e a aceitação do aviso de consentimento. Depois, eles podem gravar um vídeo curto, assistir à gravação e refazê-la antes do envio. A aplicação exibe uma confirmação após o envio e apresenta orientações quando um link expira ou ocorre algum problema.

Após o envio de um vídeo, o administrador pode assisti-lo, baixá-lo, marcá-lo como analisado ou excluí-lo. Os dados de cadastro e os registros de consentimento do solicitante continuam disponíveis após a exclusão do vídeo. O acesso às gravações é restrito aos administradores autorizados.

Também atualizamos a forma como os links de cadastro são criados. Agora, a aplicação pode usar o endereço local durante o desenvolvimento e o endereço seguro correto do site quando estiver hospedada online. Isso prepara o sistema para o compartilhamento de links com os solicitantes pelo celular. O endereço online ainda precisa ser configurado; os links locais atuais só funcionam no computador em que a aplicação está sendo executada.

O fluxo principal passou por verificações automatizadas e por um teste no navegador que incluiu cadastro, consentimento, gravação e envio de vídeo, além da análise pelo administrador. Também verificamos o comportamento dos links expirados e substituídos. Esses resultados nos dão uma base funcional, mas ainda precisamos confirmar a experiência em iPhones e celulares Android reais, usando uma conexão segura com a internet.

A versão inicial da Fase 1 foi salva no GitHub. As melhorias mais recentes para o acesso online estão disponíveis no projeto em desenvolvimento, mas ainda não foram incorporadas à versão publicada.

Para a próxima etapa, estão previstas as seguintes atividades:

1. **Disponibilizar uma versão de testes online.** Confirmar qual computador Windows será usado para a hospedagem e configurar um endereço seguro que possa ser acessado de outro notebook ou celular. Já avaliamos o uso de um endereço gratuito da Vercel, mas ainda não publicamos a aplicação nessa plataforma.
2. **Concluir a conexão entre o site e os serviços que o fazem funcionar.** Garantir que o login, a abertura dos links de convite e o envio dos vídeos funcionem pelo endereço online. Se usarmos a Vercel, será necessário ajustar o processo de envio para aceitar gravações maiores.
3. **Testar toda a experiência no celular.** Enviar um link de cadastro pelo WhatsApp, abri-lo em um iPhone e em um celular Android e verificar o acesso à câmera, a gravação, a opção de regravar, o envio e as mensagens de confirmação.
4. **Verificar a confiabilidade e a privacidade no ambiente online.** Confirmar que as gravações permanecem privadas, que seja possível tentar novamente após um envio interrompido, que os links expirados sejam tratados corretamente e que a aplicação volte a funcionar após a reinicialização do computador de hospedagem.
5. **Resolver os problemas encontrados e preparar uma demonstração.** Corrigir os pontos identificados durante os testes, atualizar a versão salva do projeto e preparar uma breve apresentação de toda a experiência do solicitante e do administrador.

O monitoramento de agendamentos e as funcionalidades do bot continuam fora do escopo atual. As mensagens pelo WhatsApp ainda são enviadas manualmente, e as gravações são analisadas por uma pessoa. A prioridade imediata é preparar uma demonstração online confiável do processo de cadastro e recebimento de vídeos que já funciona localmente.
