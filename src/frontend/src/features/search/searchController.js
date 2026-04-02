import { debounce } from "../../utils/debounce.js";
import { clearElement, createElement, setText } from "../../utils/dom.js";

export function createSearchController({
  apiClient,
  input,
  submitButton,
  suggestionsRoot,
  candidateResultsRoot,
  helperText,
  statusElement,
  onLocationResolved
}) {
  async function resolveQuery(query) {
    if (!query || query.trim().length < 3) {
      setText(helperText, "Enter more details.");
      setText(statusElement, "Waiting");
      clearElement(suggestionsRoot);
      return;
    }

    setText(statusElement, "Searching");

    try {
      const response = await apiClient.resolveAddress(query.trim());
      clearElement(candidateResultsRoot);

      if (response.status === "resolved" && response.location) {
        setText(statusElement, "Resolved");
        onLocationResolved(response.location);
        return;
      }

      if (response.status === "ambiguous") {
        setText(statusElement, "Ambiguous");
        renderCandidates(response.candidates || []);
        return;
      }

      if (response.status === "unsupported_region") {
        setText(statusElement, "Unsupported");
        setText(
          helperText,
          "Region not supported. Search for a property within Edmonton."
        );
        return;
      }

      setText(statusElement, "No match");
      setText(
        helperText,
        "No matching address found. Try postal code, city, or a more specific address."
      );
    } catch (error) {
      setText(statusElement, "Unavailable");
      setText(helperText, "Search unavailable right now. Please retry.");
    }
  }

  async function loadSuggestions(query) {
    if (!query || query.trim().length < 3) {
      clearElement(suggestionsRoot);
      return;
    }

    try {
      const response = await apiClient.getAddressSuggestions(query.trim());
      renderSuggestions(response.suggestions || []);
      setText(helperText, response.suggestions?.length ? "Suggestions" : "No suggestions found.");
    } catch (error) {
      clearElement(suggestionsRoot);
      setText(helperText, "Suggestion service unavailable.");
    }
  }

  function renderSuggestions(suggestions) {
    clearElement(suggestionsRoot);

    suggestions.forEach((suggestion) => {
      const item = createElement("button", "suggestion-item");
      item.type = "button";

      const title = createElement("div", "suggestion-title", suggestion.display_text);
      const meta = createElement(
        "div",
        "suggestion-meta",
        `${suggestion.secondary_text || ""} ${suggestion.confidence ? `· ${suggestion.confidence}` : ""}`.trim()
      );

      item.appendChild(title);
      item.appendChild(meta);
      item.addEventListener("click", () => {
        input.value = suggestion.display_text;
        resolveQuery(suggestion.display_text);
      });

      suggestionsRoot.appendChild(item);
    });
  }

  function renderCandidates(candidates) {
    clearElement(candidateResultsRoot);

    candidates.forEach((candidate) => {
      const item = createElement("button", "candidate-item");
      item.type = "button";

      item.appendChild(
        createElement("div", "candidate-title", candidate.display_text)
      );
      item.appendChild(
        createElement(
          "div",
          "candidate-copy",
          candidate.coverage_status === "supported"
            ? "Candidate address"
            : "Outside supported coverage"
        )
      );

      item.addEventListener("click", () => {
        onLocationResolved({
          canonical_location_id: candidate.candidate_id || null,
          canonical_address: candidate.display_text,
          coordinates: candidate.coordinates,
          region: "Edmonton",
          neighbourhood: null,
          coverage_status: candidate.coverage_status
        });
      });

      candidateResultsRoot.appendChild(item);
    });
  }

  const debouncedSuggestionLoader = debounce(loadSuggestions, 300);

  input.addEventListener("input", (event) => {
    debouncedSuggestionLoader(event.target.value);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      resolveQuery(input.value);
    }
  });

  submitButton.addEventListener("click", () => resolveQuery(input.value));
}
