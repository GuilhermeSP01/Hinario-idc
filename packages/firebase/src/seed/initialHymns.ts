import type { Hymn } from '@hinario/core';

export const INITIAL_HINARIO_VERSION = 1;

/**
 * Snapshot inicial embutido no aplicativo para funcionamento 100% offline desde o primeiro acesso.
 * Quando o Firestore possuir uma versão superior a `INITIAL_HINARIO_VERSION`, o app fará o delta sync automaticamente.
 */
export const INITIAL_HYMNS_SEED: Hymn[] = [
  {
    id: '001',
    number: 1,
    title: 'Chuvas de Graça',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Deus prometeu com certeza',
          'Chuvas de graça mandar;',
          'Ele nos dá fortaleza,',
          'E ricas bênçãos sem par.',
        ],
      },
      {
        type: 'chorus',
        lines: [
          'Chuvas de graça,',
          'Chuvas pedimos, Senhor;',
          'Manda-nos chuvas constantes,',
          'Chuvas do Consolador.',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Cristo nos tem concedido',
          'O santo Consolador,',
          'De plena paz nos enchido,',
          'Para o reinado do amor.',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Dá-nos, Senhor, amplamente,',
          'Teu grande gozo e poder;',
          'Fonte de amor permanente,',
          'Põe dentro de nosso ser.',
        ],
      },
      {
        type: 'verse',
        number: 4,
        lines: [
          'Faze os teus servos piedosos,',
          'Dá-lhes virtude e valor,',
          'Dando os teus dons preciosos,',
          'Do santo Preceptor.',
        ],
      },
    ],
  },
  {
    id: '002',
    number: 2,
    title: 'Saudai o Nome de Jesus',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Saudai o nome de Jesus!',
          'Arcanjos, vos prostrai;',
          'Ao Filho do eterno Deus',
          'Com glória coroai!',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Ó escolhida geração',
          'Do bom e eterno Pai,',
          'Ao grande Autor da salvação',
          'Com glória coroai!',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Ó perdoados, cujo amor',
          'Bem triunfante vai,',
          'Ao Deus varão, Conquistador,',
          'Com glória coroai!',
        ],
      },
      {
        type: 'verse',
        number: 4,
        lines: [
          'Ó raças, tribos e nações,',
          'Ao Rei divino honrai!',
          'A quem quebrou vossos grilhões,',
          'Com glória coroai!',
        ],
      },
    ],
  },
  {
    id: '003',
    number: 3,
    title: 'Grandioso És Tu',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Senhor meu Deus, quando eu, maravilhado,',
          'Fico a pensar nas obras de tuas mãos,',
          'No céu azul de estrelas pontilhado,',
          'O teu poder mostrando a criação;',
        ],
      },
      {
        type: 'chorus',
        lines: [
          'Então minh’alma canta a Ti, Senhor:',
          'Grandioso és Tu! Grandioso és Tu!',
          'Então minh’alma canta a Ti, Senhor:',
          'Grandioso és Tu! Grandioso és Tu!',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Quando a vagar nas matas e florestas,',
          'O passaredo alegre ouço a cantar,',
          'Olhando os montes, vales e campinas,',
          'Em tudo vejo o teu poder sem par.',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Quando eu medito em teu amor tão grande,',
          'Teu Filho dando ao mundo pra salvar,',
          'Na cruz vertendo o seu precioso sangue,',
          'Minh’alma pode assim purificar.',
        ],
      },
      {
        type: 'verse',
        number: 4,
        lines: [
          'E quando, enfim, Jesus vier em glória',
          'E ao lar celeste então me transportar,',
          'Te adorarei, prostrado e para sempre:',
          'Grandioso és Tu, meu Deus, hei de cantar!',
        ],
      },
    ],
  },
  {
    id: '004',
    number: 4,
    title: 'Castelo Forte',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Castelo forte é nosso Deus,',
          'Espada e bom escudo;',
          'Com seu poder defende os seus',
          'Em todo transe agudo.',
          'Com fúria pertinaz',
          'Persegue Satanás,',
          'Com ânimo cruel;',
          'Muito forte é o Deus fiel,',
          'Igual não há na terra.',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'A nossa força nada faz:',
          'Estamos, sim, perdidos;',
          'Mas nosso Deus socorro traz',
          'E somos protegidos.',
          'Defende-nos Jesus,',
          'O que venceu na cruz,',
          'Senhor dos altos céus;',
          'E, sendo o próprio Deus,',
          'Triunfa na batalha.',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Sim, que a Palavra ficará,',
          'Sabemos com certeza,',
          'E nada nos assustará',
          'Com Cristo por defesa.',
          'Se temos de perder',
          'Família, bens, prazer,',
          'Se tudo se acabar',
          'E a morte enfim chegar,',
          'Com Ele reinaremos!',
        ],
      },
    ],
  },
  {
    id: '005',
    number: 5,
    title: 'Mais Perto Quero Estar',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Mais perto quero estar,',
          'Meu Deus, de Ti!',
          'Inda que seja a dor',
          'Que me una a Ti.',
          'Sempre hei de suplicar:',
          'Mais perto quero estar,',
          'Meu Deus, de Ti!',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Andando triste aqui,',
          'Na solidão,',
          'Paz e descanso a mim',
          'Teus braços dão.',
          'Nas trevas vou sonhar:',
          'Mais perto quero estar,',
          'Meu Deus, de Ti!',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Minh’alma cantará',
          'A Ti, Senhor!',
          'E em Betel alçará',
          'Padrão de amor.',
          'Eu sempre hei de rogar:',
          'Mais perto quero estar,',
          'Meu Deus, de Ti!',
        ],
      },
    ],
  },
  {
    id: '006',
    number: 6,
    title: 'Santo! Santo! Santo!',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Santo! Santo! Santo! Deus Onipotente!',
          'Cedo de manhã cantaremos Teu louvor.',
          'Santo! Santo! Santo! Deus Jeová Triúno!',
          'És um só Deus, excelso Criador.',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Santo! Santo! Santo! Todos os remidos,',
          'Juntos com os anjos, proclamam Teu louvor;',
          'Antes de formar-se o firmamento e a terra,',
          'Eras, e sempre és, e hás de ser, Senhor.',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Santo! Santo! Santo! Nós, os pecadores,',
          'Não podemos ver Tua glória sem temor;',
          'Tu somente és Santo; não há nenhum outro,',
          'Puro e perfeito, excelso Benfeitor.',
        ],
      },
    ],
  },
  {
    id: '007',
    number: 7,
    title: 'Rocha Eterna',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Rocha eterna, foi na cruz',
          'Que morreste Tu, Jesus.',
          'Vem de Ti um sangue tal',
          'Que me limpa todo o mal;',
          'Traz as bênçãos do perdão:',
          'Gozo, paz e salvação.',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Não trabalho pra alcançar',
          'Tua graça singular;',
          'Não descansa o meu labor,',
          'Não apaga a minha dor;',
          'Só Tu podes, ó Jesus,',
          'Dar-me vida, paz e luz.',
        ],
      },
      {
        type: 'verse',
        number: 3,
        lines: [
          'Nada trago a Ti, Senhor!',
          'Confio só no Teu amor!',
          'Todo indigno e vil que sou,',
          'Para a Tua fonte vou;',
          'Lava-me, ó Salvador,',
          'Senão morro, pecador!',
        ],
      },
    ],
  },
  {
    id: '008',
    number: 8,
    title: 'Quão Bondoso Amigo é Cristo',
    version: 1,
    sections: [
      {
        type: 'verse',
        number: 1,
        lines: [
          'Quão bondoso Amigo é Cristo!',
          'Carregou com a nossa dor,',
          'E nos manda que levemos',
          'Os cuidados ao Senhor.',
          'Falta ao coração dorido',
          'Gozo, paz, consolação?',
          'Isso é porque não levamos',
          'Tudo a Deus em oração.',
        ],
      },
      {
        type: 'verse',
        number: 2,
        lines: [
          'Tu estás fraco e carregado',
          'De cuidados e temor?',
          'A Jesus, refúgio eterno,',
          'Vai com fé teu mal expor.',
          'Teus amigos te desprezam?',
          'Conta-Lhe isso em oração,',
          'E com Seu amor tão terno',
          'Paz terás no coração.',
        ],
      },
    ],
  },
];
