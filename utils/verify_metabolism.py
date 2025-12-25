import time
import sys
import os

# Aggiungi il path per importare raiven se necessario
sys.path.append(os.path.join(os.getcwd(), "src"))

from raiven import CognitiveMemory

def test_subconscious_active():
    brain = CognitiveMemory()
    test_string = f"METABOLISM_VERIFICATION_{int(time.time())}"
    
    print(f"--- Inizio Test Subconscio ---")
    print(f"1. Inserimento memoria di test: '{test_string}'")
    
    # Inseriamo la memoria. Di default 'needs_embedding' sarà true.
    brain.add_memory(
        text=f"Test di attivazione metabolismo: {test_string}. Se questo flag scompare, il processo è vivo.",
        entities=["Test", "Metabolismo"]
    )
    
    print("2. Memoria inserita. Controllo lo stato del flag 'needs_embedding'...")
    
    # Verifichiamo lo stato iniziale
    query = f"MATCH (c:Chunk) WHERE c.text CONTAINS '{test_string}' RETURN c.needs_embedding as needs"
    
    attempts = 0
    max_attempts = 6 # 6 * 10 secondi = 1 minuto
    
    while attempts < max_attempts:
        result = brain._query_neo4j(query)
        try:
            needs_embedding = result["results"][0]["data"][0]["row"][0]
        except (IndexError, KeyError):
            print("Errore nel recupero del dato.")
            break
            
        if needs_embedding is False or needs_embedding is None:
            print(f"\n[SUCCESS] Il metabolismo ha processato la memoria!")
            print(f"Il flag 'needs_embedding' è ora: {needs_embedding}")
            return True
        else:
            print(f"Tentativo {attempts+1}/{max_attempts}: Il flag è ancora TRUE. Il metabolismo sta lavorando (attesa 10s)...")
            time.sleep(10)
            attempts += 1
            
    print("\n[TIMEOUT] Il metabolismo non ha processato la memoria in tempo.")
    print("Verifica che 'raiven_metabolism.py' sia in esecuzione con 'ps aux'.")
    return False

if __name__ == "__main__":
    test_subconscious_active()
