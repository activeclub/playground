import { GetMessages } from "@/app/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/config";
import { GalleryVerticalEnd } from "lucide-react";

export default async function LoginPage() {
  const ret = await fetch(`${API_BASE_URL}/api/messages`, { method: "GET" });
  const { data: messages } = (await ret.json()) as GetMessages;

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <a href="#" className="flex items-center gap-2 self-center font-medium">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <GalleryVerticalEnd className="size-4" />
          </div>
          Wondy
        </a>
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="text-xl">Welcome back</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {messages.map((msg) =>
                  msg.speaker === "SYSTEM" ? (
                    <div key={msg.id} className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 bg-muted">
                      Hi, how can I help you today?
                    </div>
                  ) : msg.speaker === "USER" ? (
                    <div key={msg.id} className="flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 ml-auto bg-primary text-primary-foreground">
                      Hey, I'm having trouble with my account.
                    </div>
                  ) : (
                    <></>
                  )
                )}
              </div>
            </CardContent>
          </Card>
          <div className="text-balance text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4 [&_a]:hover:text-primary  ">
            By clicking continue, you agree to our{" "}
            <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>.
          </div>
        </div>
      </div>
    </div>
  );
}
