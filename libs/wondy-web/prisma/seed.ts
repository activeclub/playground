import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("Start truncating ...");
  for (const { table_name } of await prisma.$queryRaw<
    { table_name: string }[]
  >`SELECT table_name FROM information_schema.tables WHERE table_schema='public';`) {
    await prisma.$executeRawUnsafe(
      `TRUNCATE TABLE "${table_name}" RESTART IDENTITY CASCADE;`
    );
  }
  console.log("Truncating finished.");

  console.log("Start seeding ...");
  await prisma.message.createMany({
    data: [
      {
        contentAudio: new Uint8Array(new ArrayBuffer(0)),
        contentTranscript: "Hi, how can I help you today?",
        speaker: "SYSTEM",
      },
      {
        contentAudio: new Uint8Array(new ArrayBuffer(0)),
        contentTranscript: "Hey, I'm having trouble with my account.",
        speaker: "USER",
      },
    ],
  });
  console.log("Seeding finished.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
