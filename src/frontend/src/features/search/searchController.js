/* node:coverage disable */
import { debounce } from "../../utils/debounce.js";
import { clearElement, createElement, setText } from "../../utils/dom.js";
import {
  SEARCH_INPUT_DEBOUNCE_MS,
  SEARCH_QUERY_MIN_CHARS,
  SEARCH_SUGGESTIONS_DEFAULT_LIMIT
} from "../../config.js";

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
    if (!query || query.trim().length < SEARCH_QUERY_MIN_CHARS) {
      setText(helperText, "Enter more details.");
      setText(statusElement, "Waiting");
      clearElement(suggestionsRoot);
      clearElement(candidateResultsRoot);
      return;
    }

    setText(statusElement, "Searching");

    try {
      const response = await apiClient.resolveAddress(query.trim());
      clearElement(suggestionsRoot);
      clearElement(candidateResultsRoot);

      if (response.status === "resolved" && response.location) {
        setText(statusElement, "Resolved");
        setText(helperText, "Address resolved.");
        clearElement(suggestionsRoot);
        clearElement(candidateResultsRoot);
        onLocationResolved(response.location);
        return;
      }

      if (response.status === "ambiguous") {
        setText(statusElement, "Ambiguous");
        setText(helperText, "Multiple candidate addresses found.");
        clearElement(suggestionsRoot);
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
      clearElement(candidateResultsRoot);
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
    if (!query || query.trim().length < SEARCH_QUERY_MIN_CHARS) {
      clearElement(suggestionsRoot);
      clearElement(candidateResultsRoot);
      return;
    }

    try {
      const response = await apiClient.getAddressSuggestions(query.trim(), SEARCH_SUGGESTIONS_DEFAULT_LIMIT);
      renderSuggestions(response.suggestions || []);
      setText(helperText, response.suggestions?.length ? "Suggestions" : "No suggestions found.");
    } catch (error) {
      clearElement(suggestionsRoot);
      setText(helperText, "Suggestion service unavailable.");
    }
  }

  /* node:coverage disable */
  function renderSuggestions(suggestions) {
    clearElement(suggestionsRoot);

    suggestions.forEach((suggestion) => {
      const item = createElement("button", "suggestion-item");
      item.type = "button";

      const title = createElement("div", "suggestion-title", suggestion.display_text);
      /* node:coverage ignore next */
      const meta = createElement("div", "suggestion-meta", `${suggestion.secondary_text || ""} ${suggestion.confidence ? `· ${suggestion.confidence}` : ""}`.trim());

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
      /* node:coverage ignore next */
      item.appendChild(createElement("div", "candidate-copy", candidate.coverage_status === "supported"
        ? "Candidate address"
        : "Outside supported coverage"));

      item.addEventListener("click", () => {
        const canonicalLocationId = candidate.canonical_location_id
          || candidate.location_id
          || (
            typeof candidate.candidate_id === "string" && candidate.candidate_id.startsWith("cand_")
              ? candidate.candidate_id.slice(5)
              : candidate.candidate_id
          )
          || null;

        onLocationResolved({
          canonical_location_id: canonicalLocationId,
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
  /* node:coverage enable */

  const debouncedSuggestionLoader = debounce(loadSuggestions, SEARCH_INPUT_DEBOUNCE_MS);

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

  return {
    resolveQuery,
    setQuery(value) {
      input.value = value;
    },
    clear() {
      input.value = "";
      clearElement(suggestionsRoot);
      clearElement(candidateResultsRoot);
      setText(helperText, `Enter at least ${SEARCH_QUERY_MIN_CHARS} characters to load suggestions.`);
      setText(statusElement, "Idle");
    }
  };
}
