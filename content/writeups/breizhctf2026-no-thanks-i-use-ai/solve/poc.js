(async () => {
      const oldname = "dotenv.py";
      const newname = "../dotenv.py";

      const res = await fetch('/api/admin/files/move', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: oldname, newFilename: newname })
      });
  })();