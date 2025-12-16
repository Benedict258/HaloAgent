import { useEffect, useRef, useCallback, useState } from "react";
import { cn } from "@/lib/utils";
import { SendIcon, LoaderIcon } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import * as React from "react";

interface Message {
  id: string | number;
  direction: "IN" | "OUT";
  content: string;
  created_at: string;
}

interface AnimatedAIChatProps {
  businessId: string;
  contactPhone: string;
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
}

export function AnimatedAIChat({ 
  businessId, 
  contactPhone, 
  messages, 
  onSendMessage,
  isLoading = false 
}: AnimatedAIChatProps) {
  const [value, setValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (value.trim() && !isSending) {
      setIsSending(true);
      try {
        await onSendMessage(value.trim());
        setValue("");
        if (textareaRef.current) {
          textareaRef.current.style.height = "60px";
        }
      } catch (error) {
        console.error("Failed to send message:", error);
      } finally {
        setIsSending(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "60px";
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              <h2 className="text-2xl font-semibold text-black">Start a conversation</h2>
              <p className="text-gray-600">Ask about our products, place an order, or get support</p>
            </motion.div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex",
                  message.direction === "IN" ? "justify-end" : "justify-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[70%] rounded-lg px-4 py-2",
                    message.direction === "IN"
                      ? "bg-brand text-white"
                      : "bg-gray-100 text-black"
                  )}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className={cn(
                    "text-xs mt-1",
                    message.direction === "IN" ? "text-white/70" : "text-gray-500"
                  )}>
                    {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </motion.div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}

        {/* Typing Indicator */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="flex justify-start"
            >
              <div className="bg-gray-100 rounded-lg px-4 py-3">
                <TypingDots />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent min-h-15 max-h-50"
            style={{ overflow: "hidden" }}
          />
          <motion.button
            type="button"
            onClick={handleSendMessage}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            disabled={isSending || !value.trim()}
            className={cn(
              "px-4 py-3 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
              value.trim() && !isSending
                ? "bg-brand text-white hover:bg-brand/90"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            )}
          >
            {isSending ? (
              <LoaderIcon className="w-4 h-4 animate-spin" />
            ) : (
              <SendIcon className="w-4 h-4" />
            )}
            <span>Send</span>
          </motion.button>
        </div>
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3].map((dot) => (
        <motion.div
          key={dot}
          className="w-2 h-2 bg-gray-400 rounded-full"
          initial={{ opacity: 0.3 }}
          animate={{
            opacity: [0.3, 1, 0.3],
            scale: [0.85, 1.1, 0.85]
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: dot * 0.15,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
