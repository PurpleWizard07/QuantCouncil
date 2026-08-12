import { MDXRemote } from "next-mdx-remote/rsc";
import rehypeKatex from "rehype-katex";
import rehypeSlug from "rehype-slug";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { mdxComponents } from "@/app/learn/lib/mdxComponents";

/** Compiles and renders one lesson's raw MDX source with the full plugin chain. */
export function LessonContent({ source }: { source: string }) {
  return (
    <MDXRemote
      source={source}
      components={mdxComponents}
      options={{
        mdxOptions: {
          remarkPlugins: [remarkGfm, remarkMath],
          rehypePlugins: [rehypeSlug, rehypeKatex],
        },
      }}
    />
  );
}
