- Write SOLID, readable, and maintainable code
- Write comments in English
  - Comments should be concise. Should be only single line per topic.
    - There is NO need to leave comments for each code update.
      - ex: "This code is left because of..."
      - ex: "This code is deleted because of..."
    - Be aware if the code readers would prefer to read your comments, or it is just noise for them.
  - Write comments for the responsibility of the file itself at the top
  - Write comments for each public class/method/variable
    - If Python, write in docstring format
    - If C#, write in XML format
    - If TypeScript, write in TSDoc format
- Prepare English and Japanese versions for all documents.
- all in-UI text should be in English by default, but support Japanese localization.
- Everytime updated the code, check all documents and update them if necessary.
- Debug the frontend by yourself
- Make granular commits for each unit of implementation. One commit per small, self-contained
  unit. Do not bundle a whole subsystem into one commit. Commit each unit as soon as its checks pass.
- If you use Python
  - Use `uv` for package management
  - Enable strict typing
  - Add appropriate package for better code/quality
- If you use JavaScript/TypeScript
  - Use `pnpm` for package management
  - Add appropriate package for better code/quality
  - Use Vue for frontend
    - Granular components are preferred.
  - Write in Single File Component style, such as

```vue
<template>HTML</template>
<script>
export default {
  name:...
}
</script>
<style scoped></style>
```

- Write documents to understand the code architecture. Such as: class diagram, sequence diagram...
