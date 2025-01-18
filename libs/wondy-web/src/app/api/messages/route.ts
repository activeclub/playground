import { Prisma, PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const defaultSelect = Prisma.validator<Prisma.MessageDefaultArgs>()({
  select: {
    id: true,
    contentTranscript: true,
    speaker: true,
    sentAt: true,
  },
});

type Message = Prisma.MessageGetPayload<typeof defaultSelect>;

export type GetMessages = {
  data: Message[];
};

export async function GET(request: Request) {
  const messages = await prisma.message.findMany({
    select: defaultSelect.select,
  });

  const res: GetMessages = { data: messages };

  return Response.json(res);
}
