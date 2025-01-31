import { GetMessages } from "@/app/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/config";
import { dayjs } from "@/lib/dayjs";

export default async function LoginPage() {
  const ret = await fetch(`${API_BASE_URL}/api/messages`, { method: "GET" });
  const { data: messages } = (await ret.json()) as GetMessages;
  console.log(messages);

  return (
    <div className="flex min-h-svh flex-col items-center justify-start gap-6 bg-muted p-6 md:p-10">
      <div className="flex min-w-full max-w-sm flex-col gap-6">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader></CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Array.from(messages)
                  .filter((msg) => msg.contentTranscript)
                  .sort((a, b) => dayjs(a.sentAt).diff(dayjs(b.sentAt)))
                  .map((msg) =>
                    msg.speaker === "SYSTEM" ? (
                      <div
                        key={msg.id}
                        className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 bg-muted"
                      >
                        {msg.contentTranscript}
                      </div>
                    ) : msg.speaker === "USER" ? (
                      <div
                        key={msg.id}
                        className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 ml-auto bg-primary text-primary-foreground"
                      >
                        {msg.contentTranscript}
                      </div>
                    ) : (
                      <></>
                    )
                  )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
